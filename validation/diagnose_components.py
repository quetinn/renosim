"""Engine vs DPE, step by step along the calculation chain (recalibration diagnosis).

For each segment (construction period, main heating energy) of a sample, the
script compares the engine with the published DPE at every stage it can:

1. envelope losses   GV           vs ``deperditions_enveloppe`` (W/K)
2. heating need      Bch          vs ``besoin_chauffage`` (kWh)
3. DHW need          Becs         vs ``besoin_ecs`` (kWh)
4. heating final energy           vs ``conso_chauffage_ef`` (sidecar, optional)
5. primary energy    Cep          vs ``conso_5_usages_par_m2_ep`` (bias, kWhep/m2)

Ratios are aggregate ratios (sum engine / sum DPE) so large houses weigh by
their energy. The output tells which stage drifts first in each segment: the
place a recalibration should act on (validation note §7, protocol v1.1). It
reads the calibration sample only; never run it to tune on a test sample.

Usage:
    python validation/diagnose_components.py data/dpe_calib_v3.jsonl \
        --out validation/report/diagnosis_calib_v3.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))

from mapping import map_row
from renosim import simulate
from renosim.envelope import envelope_heat_loss

STAGES = ("gv", "heating_need", "dhw_need", "heating_final")


def _ratio(rows: list[dict[str, Any]], stage: str) -> float | None:
    pairs = [(r[stage][0], r[stage][1]) for r in rows if r[stage] is not None]
    if not pairs:
        return None
    dpe = sum(p[1] for p in pairs)
    return round(sum(p[0] for p in pairs) / dpe, 3) if dpe > 0 else None


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {"n": len(rows)}
    for stage in STAGES:
        out[f"{stage}_ratio"] = _ratio(rows, stage)
    out["cep_bias_kwhep_m2"] = round(sum(r["cep_diff"] for r in rows) / len(rows), 1)
    return out


def diagnose(sample: Path) -> dict[str, Any]:
    sidecar = sample.with_suffix(".extra.jsonl")
    extras: dict[str, dict[str, Any]] = {}
    if sidecar.exists():
        extras = {str(e["numero_dpe"]): e for e in map(json.loads, sidecar.open(encoding="utf-8"))}
    rows: list[dict[str, Any]] = []
    for line in sample.open(encoding="utf-8"):
        raw = json.loads(line)
        m = map_row(raw)
        if m.building is None or m.observed_cep is None:
            continue
        sim = simulate(m.building, regulation_vintage=m.regulation_vintage)  # type: ignore[arg-type]
        gv = envelope_heat_loss(m.building).gv_w_per_k
        extra = extras.get(str(raw["numero_dpe"]), {})

        def pair(engine: float, field: Any) -> tuple[float, float] | None:
            return (engine, float(field)) if field not in (None, 0, "") else None

        rows.append(
            {
                "period": str(raw.get("periode_construction")),
                "energy": str(raw.get("type_energie_principale_chauffage")),
                "gv": pair(gv, raw.get("deperditions_enveloppe")),
                "heating_need": pair(sim.needs.heating_kwh, raw.get("besoin_chauffage")),
                "dhw_need": pair(sim.needs.dhw_kwh, raw.get("besoin_ecs")),
                "heating_final": pair(
                    sim.final_energy_kwh_by_use.get("heating", 0.0),
                    extra.get("conso_chauffage_ef"),
                ),
                "cep_diff": sim.primary_energy_kwh_m2 - float(m.observed_cep),
            }
        )
    by: dict[str, dict[str, list[dict[str, Any]]]] = {
        "period": defaultdict(list),
        "energy": defaultdict(list),
    }
    for r in rows:
        by["period"][r["period"]].append(r)
        by["energy"][r["energy"]].append(r)
    return {
        "sample": str(sample).replace("\\", "/"),
        "sidecar_used": sidecar.exists(),
        "overall": _summary(rows),
        "by_period": {k: _summary(v) for k, v in sorted(by["period"].items())},
        "by_energy": {k: _summary(v) for k, v in sorted(by["energy"].items())},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sample", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = diagnose(args.sample)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    print(f"{'segment':<45} {'n':>5} {'GV':>6} {'Bch':>6} {'Becs':>6} {'Cch':>6} {'bias':>7}")
    for group in ("by_period", "by_energy"):
        for key, s in report[group].items():
            cells = [s[f"{st}_ratio"] for st in STAGES]
            text = " ".join(f"{c:>6.3f}" if c is not None else f"{'-':>6}" for c in cells)
            print(f"{key:<45} {s['n']:>5} {text} {s['cep_bias_kwhep_m2']:>+7.1f}")
    o = report["overall"]
    print(
        f"{'ALL':<45} {o['n']:>5} "
        + " ".join(
            f"{o[f'{st}_ratio']:>6.3f}" if o[f"{st}_ratio"] is not None else f"{'-':>6}"
            for st in STAGES
        )
        + f" {o['cep_bias_kwhep_m2']:>+7.1f}"
    )


if __name__ == "__main__":
    main()
