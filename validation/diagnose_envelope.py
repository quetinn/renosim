"""Engine vs DPE, envelope component by component (recalibration diagnosis).

Compares, per construction period, the engine's losses of each envelope
component with the per-component losses published in the ADEME dataset
(sidecar written by enrich_sample.py): walls, top floors, ground floors,
windows + doors, thermal bridges, air renewal, and the heating-season solar
and internal gains. It also derives an *implied window area* from the
published window losses and the engine's window U-value, to source the range
of the reconstructed window-area fraction (recalibration plan, P1).

Calibration sample only (validation note §7); never run on a test sample to
tune the engine.

Usage:
    python validation/diagnose_envelope.py data/dpe_calib_v3.jsonl \
        --out validation/report/diagnosis_envelope_calib_v3.json
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))

from mapping import map_row
from renosim.envelope import envelope_heat_loss

#: (label, engine attribute(s), ADEME field(s)) per compared component.
COMPONENTS: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
    ("walls", ("walls_w_per_k",), ("deperditions_murs",)),
    ("roof", ("roof_w_per_k",), ("deperditions_planchers_hauts",)),
    ("floor", ("floor_w_per_k",), ("deperditions_planchers_bas",)),
    ("windows_doors", ("windows_w_per_k",), ("deperditions_baies_vitrees", "deperditions_portes")),
    ("thermal_bridges", ("thermal_bridges_w_per_k",), ("deperditions_ponts_thermiques",)),
    (
        "air_renewal",
        ("ventilation_w_per_k", "infiltration_w_per_k"),
        ("deperditions_renouvellement_air",),
    ),
)


def _num(value: Any) -> float | None:
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def diagnose(sample: Path) -> dict[str, Any]:
    extras = {
        str(e["numero_dpe"]): e
        for e in map(json.loads, sample.with_suffix(".extra.jsonl").open(encoding="utf-8"))
    }
    sums: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(lambda: [0.0, 0.0]))
    window_fraction: dict[str, list[float]] = defaultdict(list)
    counts: dict[str, int] = defaultdict(int)
    for line in sample.open(encoding="utf-8"):
        raw = json.loads(line)
        m = map_row(raw)
        b = m.building
        extra = extras.get(str(raw["numero_dpe"]))
        if b is None or extra is None:
            continue
        period = str(raw.get("periode_construction"))
        env = envelope_heat_loss(b)
        counts[period] += 1
        for label, attrs, fields in COMPONENTS:
            dpe_values = [_num(extra.get(f)) for f in fields]
            if any(v is None for v in dpe_values):
                continue
            engine = sum(float(getattr(env, a)) for a in attrs)
            for key in (period, "ALL"):
                sums[key][label][0] += engine
                sums[key][label][1] += sum(v for v in dpe_values if v is not None)
        # Implied window area = published window losses / engine window U (same glazing class).
        dpe_windows = _num(extra.get("deperditions_baies_vitrees"))
        win = b.windows[0]
        if dpe_windows and win.u_value_w_per_m2k > 0:
            area = dpe_windows / (win.u_value_w_per_m2k * win.unheated_space_reduction_coefficient)
            window_fraction[period].append(area / b.living_area_m2)
            window_fraction["ALL"].append(area / b.living_area_m2)

    def ratios(key: str) -> dict[str, float | None]:
        return {label: round(e / d, 3) if d > 0 else None for label, (e, d) in sums[key].items()}

    def fraction_stats(values: list[float]) -> dict[str, float]:
        q = statistics.quantiles(values, n=10)
        return {
            "median": round(statistics.median(values), 3),
            "p10": round(q[0], 3),
            "p90": round(q[-1], 3),
        }

    return {
        "sample": str(sample).replace("\\", "/"),
        "note": "Ratios = sum(engine) / sum(DPE) per component; implied window-area "
        "fraction = deperditions_baies_vitrees / (U_window * b) / Sh.",
        "by_period": {
            key: {
                "n": counts[key],
                "ratios": ratios(key),
                "implied_window_area_fraction": fraction_stats(window_fraction[key]),
            }
            for key in sorted(counts)
        },
        "overall": {
            "ratios": ratios("ALL"),
            "implied_window_area_fraction": fraction_stats(window_fraction["ALL"]),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sample", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = diagnose(args.sample)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    labels = [c[0] for c in COMPONENTS]
    print(f"{'period':<14}" + "".join(f"{lab[:9]:>10}" for lab in labels) + f"{'win/Sh':>10}")
    rows = [*report["by_period"].items(), ("ALL", report["overall"])]
    for key, s in rows:
        r = s["ratios"]
        cells = "".join(f"{r[lab]:>10.3f}" if r.get(lab) else f"{'-':>10}" for lab in labels)
        print(f"{key:<14}{cells}{s['implied_window_area_fraction']['median']:>10.3f}")


if __name__ == "__main__":
    main()
