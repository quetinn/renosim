"""Fit the per-label U factors of mapping choice M-14 (recalibration v1.1, step A).

For houses of the calibration sample, the engine's losses of each opaque element
(walls, top floor, ground floor) are compared with the per-component losses
published in the DPE (sidecar ``*.extra.jsonl``). The cells are (element, era
before/from 1975, ADEME quality label or "absent"); in each cell with at least
``MIN_ROWS`` houses the factor is sum(DPE losses) / sum(engine losses), so that
the reconstructed inputs reproduce the published ones on aggregate. The fit
uses input losses only, never the consumption or the label.

Calibration sample only (recalibration plan, docs/recalibration_v1.1.md).

Usage:
    python validation/fit_quality_labels.py data/dpe_calib_v3.jsonl \
        --out validation/report/quality_label_factors_v3.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))

import mapping
from mapping import _roof_quality, map_row
from renosim.envelope import envelope_heat_loss
from renosim.models import DwellingType

MIN_ROWS = 30

#: element -> (engine attribute, ADEME per-component field, ADEME quality field or None for roof)
ELEMENTS = {
    "walls": ("walls_w_per_k", "deperditions_murs", "qualite_isolation_murs"),
    "roof": ("roof_w_per_k", "deperditions_planchers_hauts", None),
    "floor": ("floor_w_per_k", "deperditions_planchers_bas", "qualite_isolation_plancher_bas"),
}


def fit(sample: Path) -> dict[str, Any]:
    mapping.QUALITY_LABEL_FACTORS = {}  # fit against the unfactored mapping
    extras = {
        str(e["numero_dpe"]): e
        for e in map(json.loads, sample.with_suffix(".extra.jsonl").open(encoding="utf-8"))
    }
    cells: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0, 0.0])
    for line in sample.open(encoding="utf-8"):
        raw = json.loads(line)
        m = map_row(raw)
        b = m.building
        extra = extras.get(str(raw["numero_dpe"]))
        if b is None or extra is None or b.dwelling_type is not DwellingType.HOUSE:
            continue
        early = str(raw.get("periode_construction")) in ("avant 1948", "1948-1974")
        era = "pre1975" if early else "1975+"
        env = envelope_heat_loss(b)
        for element, (attr, field, quality_field) in ELEMENTS.items():
            dpe = extra.get(field)
            if dpe is None:
                continue
            label = _roof_quality(raw) if quality_field is None else raw.get(quality_field)
            key = f"{element}|{era}|{label or 'absent'}"
            cell = cells[key]
            cell[0] += float(getattr(env, attr))
            cell[1] += float(dpe)
            cell[2] += 1
    factors = {}
    for key, (engine, dpe, n) in sorted(cells.items()):
        factor = dpe / engine if n >= MIN_ROWS and engine > 0 else 1.0
        factors[key] = {
            "factor": round(factor, 4),
            "n": int(n),
            "engine_mean_w_per_k": round(engine / n, 1),
            "dpe_mean_w_per_k": round(dpe / n, 1),
        }
    return {
        "_meta": {
            "description": "Choice M-14 (validation/mapping.py): U factor per (element, era, "
            "ADEME quality label) so that aggregated element losses match the per-component "
            "losses published in the DPE of the calibration sample. Houses only.",
            "sample": str(sample).replace("\\", "/"),
            "fitted_on": "deperditions_murs / deperditions_planchers_hauts / "
            "deperditions_planchers_bas (ADEME dataset dpe03existant, Licence Ouverte v2.0)",
            "min_rows_per_cell": MIN_ROWS,
            "date": date.today().isoformat(),
        },
        "factors": factors,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sample", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = fit(args.sample)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    for key, cell in report["factors"].items():
        print(f"{key:<32} n={cell['n']:>5}  factor={cell['factor']:.3f}")


if __name__ == "__main__":
    main()
