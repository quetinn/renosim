"""Grid search of the v1.1 recalibration, step B (docs/recalibration_v1.1.md §4-§5).

Varies, within the ranges fixed by the plan before tuning:
  P1  conventions.geometry.window_area_fraction (validation geometry, M-1)
  P4  conventions.calibrated.solar_orientation_shading_coefficient (D-06)
  P5  conventions.boiler_seasonal_blend.full_load_weight (D-08)
on the calibration sample only, and logs every trial (raw and post-stratified
metrics). The tables are patched in memory; nothing is written to engine/.

Selection rule (plan §5): highest post-stratified within-one-class agreement
among trials with a raw Cep bias in [-5, +5] kWhep/m2; ties within 0.5 point
broken by exact agreement, then by distance to the current values.

Usage:
    python validation/recalibrate_grid.py data/dpe_calib_v3.jsonl \
        --weights validation/report/stratum_counts_maisons.json \
        --out validation/report/recalibration_v1.1_grid.json
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))

import renosim.needs as needs_module
import renosim.systems as systems_module
from mapping import map_row
from renosim import simulate
from renosim.tables_io import load_table

LABELS = ["A", "B", "C", "D", "E", "F", "G"]
CURRENT = {"P1": 1.0 / 6.0, "P4": 0.5, "P5": 0.3}
GRID = {
    "P1": [0.133, 0.15, 1.0 / 6.0, 0.19, 0.211],
    "P4": [0.45, 0.5, 0.55, 0.6, 0.62],
    "P5": [0.1, 0.13, 0.2, 0.3],
}


def _set_parameters(p1: float, p4: float, p5: float) -> None:
    conventions = load_table("conventions")  # cached dict: patched in place
    conventions["geometry"]["window_area_fraction"]["value"] = p1
    conventions["calibrated"]["solar_orientation_shading_coefficient"]["value"] = p4
    conventions["boiler_seasonal_blend"]["full_load_weight"]["value"] = p5
    needs_module.SOLAR_ORIENTATION_SHADING_COEFFICIENT = p4
    systems_module.FULL_LOAD_WEIGHT = p5


def _metrics(rows: list[tuple[float, float, str, str]], weights: list[float]) -> dict[str, float]:
    total = sum(weights)
    bias = mae = exact = within1 = 0.0
    for (pred, obs, pl, ol), w in zip(rows, weights, strict=True):
        gap = abs(LABELS.index(pl) - LABELS.index(ol))
        bias += w * (pred - obs)
        mae += w * abs(pred - obs)
        exact += w * (gap == 0)
        within1 += w * (gap <= 1)
    return {
        "bias": round(bias / total, 2),
        "mae": round(mae / total, 2),
        "exact": round(exact / total, 4),
        "within1": round(within1 / total, 4),
    }


def evaluate(raws: list[dict[str, Any]], counts: dict[str, int]) -> dict[str, Any]:
    rows: list[tuple[float, float, str, str]] = []
    strata: list[str] = []
    for raw in raws:
        m = map_row(raw)
        if m.building is None or m.observed_cep is None or m.observed_label is None:
            continue
        sim = simulate(m.building, regulation_vintage=m.regulation_vintage)  # type: ignore[arg-type]
        rows.append((sim.primary_energy_kwh_m2, float(m.observed_cep), sim.label, m.observed_label))
        strata.append("|".join(map(str, m.stratum or ())))
    in_sample = Counter(strata)
    weights = [counts.get(s, 0) / in_sample[s] for s in strata]
    return {
        "n": len(rows),
        "raw": _metrics(rows, [1.0] * len(rows)),
        "post_stratified": _metrics(rows, weights),
    }


def _distance(trial: dict[str, Any]) -> float:
    return sum(abs(trial["params"][k] - v) / v for k, v in CURRENT.items())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sample", type=Path)
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    raws = [json.loads(line) for line in args.sample.open(encoding="utf-8") if line.strip()]
    counts = json.loads(args.weights.read_text(encoding="utf-8"))["counts"]
    trials = []
    for p1, p4, p5 in itertools.product(GRID["P1"], GRID["P4"], GRID["P5"]):
        _set_parameters(p1, p4, p5)
        result = evaluate(raws, counts)
        trial = {"params": {"P1": round(p1, 4), "P4": p4, "P5": p5}, **result}
        trials.append(trial)
        print(
            f"P1={p1:.3f} P4={p4:.2f} P5={p5:.2f}  raw w1={result['raw']['within1']:.3f} "
            f"bias={result['raw']['bias']:+.1f}  "
            f"post w1={result['post_stratified']['within1']:.3f}",
            flush=True,
        )
    eligible = [t for t in trials if -5.0 <= t["raw"]["bias"] <= 5.0]
    best = None
    if eligible:
        top = max(t["post_stratified"]["within1"] for t in eligible)
        tied = [t for t in eligible if t["post_stratified"]["within1"] >= top - 0.005]
        best = max(tied, key=lambda t: (t["post_stratified"]["exact"], -_distance(t)))
    report = {
        "_meta": {
            "plan": "docs/recalibration_v1.1.md (revision 1)",
            "sample": str(args.sample).replace("\\", "/"),
            "grid": GRID,
            "current": CURRENT,
            "selection_rule": "max post-stratified within-one-class among raw bias in [-5, +5]; "
            "ties within 0.5 point -> max post-stratified exact, then closest to current",
        },
        "selected": best,
        "trials": trials,
    }
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("SELECTED:", json.dumps(best, ensure_ascii=False) if best else "none eligible")


if __name__ == "__main__":
    main()
