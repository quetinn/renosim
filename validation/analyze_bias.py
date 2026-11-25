"""Diagnose the campaign-v5 bias with the enriched samples (version, per-use data).

Needs ``<sample>.extra.jsonl`` sidecars produced by enrich_sample.py. Prints and
writes (``--out``) four analyses (note de validation v2, §5.2):

1. Implied electricity primary-energy coefficient of each published DPE, from
   the EP/EF ratio of its electric uses (lighting is always electric), by DPE
   issue year: was the 2.3 -> 1.9 switch applied retroactively in the base?
2. Bias and label agreement by ``version_dpe`` (method/software version).
3. Per-use comparison engine vs DPE in final energy (heating, DHW, lighting,
   auxiliaries), by heating energy.
4. Metrics recomputed with each DPE's *implied* coefficient instead of the
   one deduced from its date.

Usage:
    python validation/analyze_bias.py data/dpe_test_v1.jsonl data/dpe_sample_v2.jsonl \
        --out validation/report/bias_analysis_v5.json
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

LABELS = "ABCDEFG"
USES = ("chauffage", "ecs", "eclairage", "auxiliaires")
ENGINE_USE = {
    "chauffage": "heating",
    "ecs": "dhw",
    "eclairage": "lighting",
    "auxiliaires": "auxiliaries",
}


def implied_coefficient(extra: dict[str, Any]) -> float | None:
    """Electricity EP/EF coefficient used by the DPE (lighting is all-electric)."""
    ep, ef = extra.get("conso_eclairage_ep"), extra.get("conso_eclairage_ef")
    if not ep or not ef or float(ef) <= 0:
        return None
    return round(float(ep) / float(ef), 2)


def _vintage_for(coef: float | None, fallback: str) -> str:
    if coef is None:
        return fallback
    if abs(coef - 2.3) < 0.05:
        return "dpe_2021"
    if abs(coef - 1.9) < 0.05:
        return "dpe_2026"
    if abs(coef - 1.7) < 0.05:
        return "dpe_2027"
    return fallback


def _summary(rows: list[dict[str, Any]], key: str = "diff") -> dict[str, float]:
    n = len(rows)
    if n == 0:
        return {"n": 0}
    return {
        "n": n,
        "cep_bias_kwhep_m2": round(sum(r[key] for r in rows) / n, 1),
        "exact": round(sum(r["exact"] for r in rows) / n, 3),
        "within1": round(sum(r["w1"] for r in rows) / n, 3),
    }


def analyse(sample: Path) -> dict[str, Any]:
    extras = {
        str(e["numero_dpe"]): e
        for e in map(json.loads, sample.with_suffix(".extra.jsonl").open(encoding="utf-8"))
    }
    rows: list[dict[str, Any]] = []
    for line in sample.open(encoding="utf-8"):
        raw = json.loads(line)
        m = map_row(raw)
        if m.building is None:
            continue
        extra = extras.get(str(raw["numero_dpe"]), {})
        coef = implied_coefficient(extra)
        by_date = m.regulation_vintage
        by_coef = _vintage_for(coef, by_date)
        sim = simulate(m.building, regulation_vintage=by_date)  # type: ignore[arg-type]
        sim_c = (
            sim if by_coef == by_date else simulate(m.building, regulation_vintage=by_coef)  # type: ignore[arg-type]
        )
        sh = m.building.living_area_m2
        obs_label = m.observed_label
        rows.append(
            {
                "year": str(raw.get("date_etablissement_dpe"))[:4],
                "version": str(extra.get("version_dpe")),
                "energy": m.stratum[2] if m.stratum else "?",
                "coef": coef,
                "diff": sim.primary_energy_kwh_m2 - m.observed_cep,
                "diff_c": sim_c.primary_energy_kwh_m2 - m.observed_cep,
                "exact": sim.label == obs_label,
                "w1": abs(LABELS.index(sim.label) - LABELS.index(obs_label)) <= 1,
                "exact_c": sim_c.label == obs_label,
                "w1_c": abs(LABELS.index(sim_c.label) - LABELS.index(obs_label)) <= 1,
                "uses": {
                    use: (
                        sim.final_energy_kwh_by_use.get(ENGINE_USE[use], 0.0) / sh,
                        float(extra[f"conso_{use}_ef"]) / sh
                        if extra.get(f"conso_{use}_ef") is not None
                        else None,
                    )
                    for use in USES
                },
            }
        )

    # 1. implied coefficient by DPE year
    coef_by_year: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in rows:
        label = "?" if r["coef"] is None else f"{r['coef']:.1f}"
        coef_by_year[r["year"]][label] += 1

    # 2. by version
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        groups[r["version"]].append(r)
    by_version = {v: _summary(g) for v, g in sorted(groups.items())}
    year_version: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        year_version[f"{r['year']} | v{r['version']}"].append(r)
    by_year_version = {k: _summary(g) for k, g in sorted(year_version.items()) if len(g) >= 30}

    # 3. per-use comparison (kWh_ef/m2, engine - DPE), by heating energy
    per_use: dict[str, dict[str, Any]] = {}
    energies: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        energies[r["energy"]].append(r)
    for energy, group in sorted(energies.items()):
        per_use[energy] = {}
        for use in USES:
            pairs = [r["uses"][use] for r in group if r["uses"][use][1] is not None]
            if not pairs:
                continue
            pred = sum(p for p, _ in pairs) / len(pairs)
            obs = sum(o for _, o in pairs) / len(pairs)
            per_use[energy][use] = {
                "n": len(pairs),
                "engine_kwh_ef_m2": round(pred, 1),
                "dpe_kwh_ef_m2": round(obs, 1),
                "ratio": round(pred / obs, 3) if obs > 0 else None,
            }

    # 4. metrics with the implied coefficient
    corrected = {
        "n": len(rows),
        "cep_bias_kwhep_m2": round(sum(r["diff_c"] for r in rows) / len(rows), 1),
        "exact": round(sum(r["exact_c"] for r in rows) / len(rows), 3),
        "within1": round(sum(r["w1_c"] for r in rows) / len(rows), 3),
    }
    return {
        "sample": str(sample).replace("\\", "/"),
        "baseline_by_date": _summary(rows),
        "implied_coefficient_by_year": {y: dict(c) for y, c in sorted(coef_by_year.items())},
        "by_version": by_version,
        "by_year_version": by_year_version,
        "per_use_by_energy": per_use,
        "metrics_with_implied_coefficient": corrected,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("samples", type=Path, nargs="+")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    report = {s.stem: analyse(s) for s in args.samples}
    text = json.dumps(report, ensure_ascii=False, indent=1)
    print(text)
    if args.out is not None:
        args.out.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
