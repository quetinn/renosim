"""Run the validation campaign: renosim (conventional mode) vs official ADEME DPEs.

Reads the gitignored sample produced by download_dpe.py, maps each row onto a
Building (mapping.py), simulates each DPE with the primary-energy convention in
force on its issue date (2.3 / 1.9 / 1.7), and reports:

- rejection rates by reason;
- mean bias / MAE / MAPE on primary energy (kWhep/m2/an);
- label confusion matrix, exact and +-1-class agreement;
- breakdown by construction period, climate zone and heating energy;
- optionally (audit 2026-11-25 §3.4): percentile bootstrap 95 % confidence
  intervals (``--bootstrap N``) and metrics post-stratified to the DPE
  population (``--weights validation/report/stratum_counts_maisons.json``,
  produced by stratum_counts.py). Without these options the report is
  unchanged (same keys, same values).

Outputs: validation/report/results_v1.json + a markdown summary.

Usage: python validation/run_validation.py [--sample data/dpe_sample.jsonl]
       [--bootstrap 1000] [--weights validation/report/stratum_counts_maisons.json]
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import cast

sys.path.insert(0, str(Path(__file__).parent))

from mapping import MappingResult, map_row
from renosim import simulate
from renosim.outputs import RegulationVintage

LABELS = ["A", "B", "C", "D", "E", "F", "G"]


def _agreement(pairs: list[tuple[str, str]]) -> tuple[float, float]:
    if not pairs:
        return 0.0, 0.0
    exact = sum(1 for p, o in pairs if p == o) / len(pairs)
    within1 = sum(1 for p, o in pairs if abs(LABELS.index(p) - LABELS.index(o)) <= 1) / len(pairs)
    return exact, within1


def _weighted_metrics(
    rows: list[tuple[float, float, str, str]], weights: list[float]
) -> dict[str, float]:
    """Bias, MAE (kWhep/m2) and label agreements, weighted by ``weights``.

    ``rows`` holds ``(pred_cep, obs_cep, pred_label, obs_label)``.
    """
    total = sum(weights)
    if total <= 0:
        return {"bias": 0.0, "mae": 0.0, "exact": 0.0, "within1": 0.0}
    bias = mae = exact = within1 = 0.0
    for (pred, obs, pl, ol), w in zip(rows, weights, strict=True):
        diff = pred - obs
        bias += w * diff
        mae += w * abs(diff)
        gap = abs(LABELS.index(pl) - LABELS.index(ol))
        exact += w * (gap == 0)
        within1 += w * (gap <= 1)
    return {
        "bias": bias / total,
        "mae": mae / total,
        "exact": exact / total,
        "within1": within1 / total,
    }


def _bootstrap_ci(
    rows: list[tuple[float, float, str, str]],
    weights: list[float],
    draws: int,
    seed: int,
) -> dict[str, list[float]]:
    """Percentile bootstrap 95 % intervals of the weighted metrics (rows resampled)."""
    rng = random.Random(seed)
    n = len(rows)
    samples: dict[str, list[float]] = {"bias": [], "mae": [], "exact": [], "within1": []}
    for _ in range(draws):
        idx = [rng.randrange(n) for _ in range(n)]
        m = _weighted_metrics([rows[i] for i in idx], [weights[i] for i in idx])
        for key, value in m.items():
            samples[key].append(value)
    ci: dict[str, list[float]] = {}
    for key, values in samples.items():
        values.sort()
        lo = values[int(0.025 * (draws - 1))]
        hi = values[int(0.975 * (draws - 1))]
        digits = 1 if key in ("bias", "mae") else 3
        ci[key] = [round(lo, digits), round(hi, digits)]
    return ci


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", type=Path, default=Path("data/dpe_sample.jsonl"))
    parser.add_argument("--out", type=Path, default=Path("validation/report/results_v1.json"))
    parser.add_argument("--bootstrap", type=int, default=0, help="bootstrap draws (0 = off)")
    parser.add_argument("--seed", type=int, default=2026, help="bootstrap RNG seed")
    parser.add_argument(
        "--weights", type=Path, default=None, help="stratum population counts (JSON)"
    )
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
        vintage = cast(RegulationVintage, m.regulation_vintage)
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

    rows = [
        (float(p["pred_cep"]), float(p["obs_cep"]), str(p["pred_label"]), str(p["obs_label"]))  # type: ignore[arg-type]
        for p in predictions
    ]
    unit = [1.0] * len(rows)
    if args.bootstrap > 0 and rows:
        report["bootstrap_95ci"] = {
            "draws": args.bootstrap,
            "seed": args.seed,
            "unweighted": _bootstrap_ci(rows, unit, args.bootstrap, args.seed),
        }
    if args.weights is not None and rows:
        population = json.loads(args.weights.read_text(encoding="utf-8"))
        counts: dict[str, int] = population["counts"]
        in_sample: Counter[str] = Counter("|".join(map(str, p["stratum"])) for p in predictions)  # type: ignore[call-overload]
        weights = [
            counts.get(key, 0) / in_sample[key]
            for key in ("|".join(map(str, p["stratum"])) for p in predictions)  # type: ignore[call-overload]
        ]
        covered = sum(counts.get(k, 0) for k in in_sample)
        weighted = _weighted_metrics(rows, weights)
        report["post_stratified"] = {
            "weights_file": str(args.weights).replace("\\", "/"),
            "population_total": population["total"],
            "population_covered_by_sample_strata": covered,
            "cep_bias_kwhep_m2": round(weighted["bias"], 1),
            "cep_mae_kwhep_m2": round(weighted["mae"], 1),
            "label_exact_agreement": round(weighted["exact"], 3),
            "label_within_one_class": round(weighted["within1"], 3),
        }
        if args.bootstrap > 0:
            report["bootstrap_95ci"]["post_stratified"] = _bootstrap_ci(
                rows, weights, args.bootstrap, args.seed
            )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)

    print(f"rows: {report['sample_rows']} | mapped: {len(mapped)} | evaluated: {n}")
    print(f"rejections: {dict(rejections)}")
    print(f"CEP bias {bias:+.1f} kWhep/m2 | MAE {mae:.1f} | MAPE {mape:.1f} %")
    print(f"labels: exact {exact:.1%} | +-1 class {within1:.1%}")
    if "post_stratified" in report:
        ps = report["post_stratified"]
        print(
            f"post-stratified: bias {ps['cep_bias_kwhep_m2']:+.1f} | "  # type: ignore[index]
            f"exact {ps['label_exact_agreement']:.1%} | "  # type: ignore[index]
            f"+-1 class {ps['label_within_one_class']:.1%}"  # type: ignore[index]
        )
    if "bootstrap_95ci" in report:
        print(f"bootstrap 95% CI: {report['bootstrap_95ci']}")
    print(f"report -> {args.out}")


if __name__ == "__main__":
    main()
