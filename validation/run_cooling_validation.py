"""Validate the cooling chain (Bfr / Cfr, 3CL §10) against the ADEME columns.

Restricted to rows declaring a cooling generator (``type_generateur_froid``):
the base only carries ``besoin_refroidissement`` (kWh/an) and
``conso_refroidissement_ep`` (kWhep/an) for air-conditioned dwellings. Reports
bias / MAE on both the useful need (poste à poste, before efficiencies) and
the primary-energy consumption, plus breakdowns by climate zone.

Usage:
    python validation/run_cooling_validation.py [--sample data/dpe_sample_v2.jsonl]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import cast

sys.path.insert(0, str(Path(__file__).parent))

from mapping import map_row
from renosim import CONVENTIONAL, EnergyCarrier
from renosim.needs import annual_needs
from renosim.outputs import RegulationVintage, primary_energy_kwh
from renosim.systems import cooling_consumption


def _metrics(pairs: list[tuple[float, float]]) -> dict[str, float | int]:
    n = len(pairs)
    if not n:
        return {"n": 0}
    diffs = [p - o for p, o in pairs]
    obs_nonzero = [(p, o) for p, o in pairs if o > 0]
    mape = (
        sum(abs(p - o) / o for p, o in obs_nonzero) / len(obs_nonzero) * 100.0
        if obs_nonzero
        else 0.0
    )
    return {
        "n": n,
        "bias_kwh": round(sum(diffs) / n, 1),
        "mae_kwh": round(sum(abs(d) for d in diffs) / n, 1),
        "mape_pct": round(mape, 1),
        "pred_mean_kwh": round(sum(p for p, _ in pairs) / n, 1),
        "obs_mean_kwh": round(sum(o for _, o in pairs) / n, 1),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", type=Path, default=Path("data/dpe_sample_v2.jsonl"))
    parser.add_argument(
        "--out", type=Path, default=Path("validation/report/results_cooling_v1.json")
    )
    args = parser.parse_args()

    need_pairs: list[tuple[float, float]] = []
    cep_pairs: list[tuple[float, float]] = []
    need_by_zone: dict[str, list[tuple[float, float]]] = defaultdict(list)
    skipped = 0
    with args.sample.open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            if not row.get("type_generateur_froid"):
                continue
            observed_need = row.get("besoin_refroidissement")
            result = map_row(row)
            if result.building is None or observed_need is None:
                skipped += 1
                continue
            building = result.building
            bfr = annual_needs(building, CONVENTIONAL).cooling_kwh
            need_pairs.append((bfr, float(observed_need)))
            need_by_zone[building.climate_zone.value].append((bfr, float(observed_need)))
            observed_cep = row.get("conso_refroidissement_ep")
            if observed_cep is not None:
                cfr_ef = cooling_consumption(building, bfr).final_energy_kwh
                vintage = cast(RegulationVintage, result.regulation_vintage)
                cfr_ep = primary_energy_kwh(cfr_ef, EnergyCarrier.ELECTRICITY, vintage)
                cep_pairs.append((cfr_ep, float(observed_cep)))

    report = {
        "scope": "rows with a declared cooling generator (type_generateur_froid)",
        "skipped": skipped,
        "cooling_need_kwh": _metrics(need_pairs),
        "cooling_need_by_zone": {z: _metrics(p) for z, p in sorted(need_by_zone.items())},
        "cooling_consumption_ep_kwh": _metrics(cep_pairs),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    print("besoin de froid (kWh/an):", report["cooling_need_kwh"])
    for z, m in sorted(need_by_zone.items()):
        print(f"  {z}: {_metrics(m)}")
    print("conso froid EP (kWhep/an):", report["cooling_consumption_ep_kwh"])
    print(f"report -> {args.out}")


if __name__ == "__main__":
    main()
