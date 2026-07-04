"""Run the validation campaign: renosim (conventional mode) vs official ADEME DPEs.

Reads the gitignored sample produced by download_dpe.py, maps each row onto a
Building (mapping.py), simulates with the dpe_2021 primary-energy convention
(matching the 2021-2025 DPE vintage of the dataset), and reports:

- rejection rates by reason;
- mean bias / MAE / MAPE on primary energy (kWhep/m2/an);
- label confusion matrix, exact and +-1-class agreement;
- breakdown by construction period, climate zone and heating energy.

Outputs: validation/report/results_v1.json + a markdown summary.

Usage: python validation/run_validation.py [--sample data/dpe_sample.jsonl]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mapping import MappingResult, map_row
from renosim import simulate

LABELS = ["A", "B", "C", "D", "E", "F", "G"]


def _agreement(pairs: list[tuple[str, str]]) -> tuple[float, float]:
    if not pairs:
        return 0.0, 0.0
    exact = sum(1 for p, o in pairs if p == o) / len(pairs)
    within1 = sum(1 for p, o in pairs if abs(LABELS.index(p) - LABELS.index(o)) <= 1) / len(pairs)
    return exact, within1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", type=Path, default=Path("data/dpe_sample.jsonl"))
    parser.add_argument("--out", type=Path, default=Path("validation/report/results_v1.json"))
    args = parser.parse_args()

    rejections: Counter[str] = Counter()
    mapped: list[MappingResult] = []
    with args.sample.open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            result = map_row(row)
            if result.building is None:
                rejections[result.reason or "?"] += 1
            else:
                mapped.append(result)

    predictions: list[dict[str, object]] = []
    errors: Counter[str] = Counter()
    for m in mapped:
        assert m.building is not None
        vintage = "dpe_2026" if m.regulation_vintage == "dpe_2026" else "dpe_2021"
        try:
            sim = simulate(m.building, regulation_vintage=vintage)  # conventional
        except Exception as exc:
            errors[type(exc).__name__] += 1
            continue
        predictions.append(
            {
                "pred_cep": sim.primary_energy_kwh_m2,
                "obs_cep": m.observed_cep,
                "pred_label": sim.label,
                "obs_label": m.observed_label,
                "stratum": m.stratum,
            }
        )

    n = len(predictions)
    diffs = [float(p["pred_cep"]) - float(p["obs_cep"]) for p in predictions]  # type: ignore[arg-type]
    bias = sum(diffs) / n if n else 0.0
    mae = sum(abs(d) for d in diffs) / n if n else 0.0
    mape = (
        sum(
            abs(d) / float(p["obs_cep"])
            for d, p in zip(diffs, predictions, strict=True)
            if float(p["obs_cep"]) > 0
        )  # type: ignore[arg-type]
        / n
        * 100.0
        if n
        else 0.0
    )

    pairs = [(str(p["pred_label"]), str(p["obs_label"])) for p in predictions]
    exact, within1 = _agreement(pairs)

    confusion: dict[str, dict[str, int]] = {o: dict.fromkeys(LABELS, 0) for o in LABELS}
    for pred, obs in pairs:
        confusion[obs][pred] += 1

    by_stratum: dict[str, dict[str, list[tuple[str, str]]]] = {
        "periode": defaultdict(list),
        "zone": defaultdict(list),
        "energie": defaultdict(list),
    }
    for p in predictions:
        stratum = p["stratum"]
        assert isinstance(stratum, list | tuple)
        period, zone, energy = stratum
        pair = (str(p["pred_label"]), str(p["obs_label"]))
        by_stratum["periode"][str(period)].append(pair)
        by_stratum["zone"][str(zone)].append(pair)
        by_stratum["energie"][str(energy)].append(pair)

    strata_metrics = {
        dim: {
            key: {
                "n": len(pair_list),
                "exact": round(_agreement(pair_list)[0], 3),
                "within1": round(_agreement(pair_list)[1], 3),
            }
            for key, pair_list in sorted(groups.items())
        }
        for dim, groups in by_stratum.items()
    }

    report = {
        "sample_rows": sum(rejections.values()) + len(mapped),
        "rejected": dict(rejections),
        "mapped": len(mapped),
        "simulation_errors": dict(errors),
        "evaluated": n,
        "cep_bias_kwhep_m2": round(bias, 1),
        "cep_mae_kwhep_m2": round(mae, 1),
        "cep_mape_pct": round(mape, 1),
        "label_exact_agreement": round(exact, 3),
        "label_within_one_class": round(within1, 3),
        "confusion_matrix_obs_rows_pred_cols": confusion,
        "by_stratum": strata_metrics,
        "success_criteria": {
            "exact_target": 0.60,
            "within1_target": 0.90,
            "exact_met": exact >= 0.60,
            "within1_met": within1 >= 0.90,
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)

    print(f"rows: {report['sample_rows']} | mapped: {len(mapped)} | evaluated: {n}")
    print(f"rejections: {dict(rejections)}")
    print(f"CEP bias {bias:+.1f} kWhep/m2 | MAE {mae:.1f} | MAPE {mape:.1f} %")
    print(f"labels: exact {exact:.1%} | +-1 class {within1:.1%}")
    print(f"report -> {args.out}")


if __name__ == "__main__":
    main()
