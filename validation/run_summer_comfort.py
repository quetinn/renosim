"""Validate the passive summer-comfort indicator against the official ADEME values.

Reads a gitignored sample produced by download_dpe.py (v2 columns), maps each
row onto a Building (mapping.py, choice M-10), assesses the annexe 9 indicator
(renosim.assess_summer_comfort) and compares it to the official
``indicateur_confort_ete`` column: 3x3 confusion matrix, exact agreement, and
per-criterion availability rates (how often each summer input was actually
observed vs defaulted).

The dataset mixes vintages of the OFFICIAL grid itself: the annexe 9 rules
implemented here (consolidated text) only stabilise in the field around 2025
(2021 DPEs agree at ~16 %, 2025+ at ~95 % — earlier software applied the
original 2021 grid, modified since). The report therefore carries agreement by
establishment year and a headline metric on the >= 2025 sub-sample
(``current_grid``), alongside the full-sample figure.

Usage:
    python validation/run_summer_comfort.py [--sample data/dpe_sample_v2.jsonl]
        [--out validation/report/results_summer_comfort_v1.json]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mapping import map_row
from renosim import assess_summer_comfort

#: ADEME wording -> engine levels, ordered worst to best.
LEVELS = ["insufficient", "medium", "good"]
_ADEME_LEVELS = {"insuffisant": "insufficient", "moyen": "medium", "bon": "good"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", type=Path, default=Path("data/dpe_sample_v2.jsonl"))
    parser.add_argument(
        "--out", type=Path, default=Path("validation/report/results_summer_comfort_v1.json")
    )
    args = parser.parse_args()

    rejections: Counter[str] = Counter()
    availability: Counter[str] = Counter()
    pairs: list[tuple[str, str, str]] = []  # (pred, obs, establishment year)
    with args.sample.open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            observed = _ADEME_LEVELS.get(str(row.get("indicateur_confort_ete") or ""))
            if observed is None:
                rejections["indicateur_ete_manquant"] += 1
                continue
            result = map_row(row)
            if result.building is None:
                rejections[result.reason or "?"] += 1
                continue
            building = result.building
            for key, known in (
                ("protection_solaire", row.get("protection_solaire_exterieure") is not None),
                ("brasseur_air", row.get("presence_brasseur_air") is not None),
                ("traversant", row.get("logement_traversant") is not None),
                ("inertie", row.get("classe_inertie_batiment") is not None),
                ("toiture", building.roof_insulated is not None),
            ):
                if known:
                    availability[key] += 1
            year = str(row.get("date_etablissement_dpe") or "")[:4]
            pairs.append((assess_summer_comfort(building).level.value, observed, year))

    def metrics(subset: list[tuple[str, str, str]]) -> dict[str, object]:
        n = len(subset)
        if not n:
            return {"n": 0}
        exact = sum(1 for p, o, _ in subset if p == o) / n
        within1 = sum(1 for p, o, _ in subset if abs(LEVELS.index(p) - LEVELS.index(o)) <= 1) / n
        confusion: dict[str, dict[str, int]] = {o: dict.fromkeys(LEVELS, 0) for o in LEVELS}
        for pred, obs, _ in subset:
            confusion[obs][pred] += 1
        return {
            "n": n,
            "exact_agreement": round(exact, 3),
            "within_one_level": round(within1, 3),
            "confusion_matrix_obs_rows_pred_cols": confusion,
        }

    n = len(pairs)
    current_grid = [p for p in pairs if p[2] >= "2025"]
    by_year = {
        year: metrics([p for p in pairs if p[2] == year]) for year in sorted({p[2] for p in pairs})
    }
    report = {
        "sample_rows": n + sum(rejections.values()),
        "rejected": dict(rejections),
        "evaluated": n,
        "all_vintages": metrics(pairs),
        "current_grid_2025_plus": metrics(current_grid),
        "by_establishment_year": {
            year: {k: v for k, v in m.items() if k != "confusion_matrix_obs_rows_pred_cols"}
            for year, m in by_year.items()
        },
        "input_availability_rate": {
            key: round(count / n, 3) for key, count in sorted(availability.items())
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)

    print(f"rows: {report['sample_rows']} | evaluated: {n} | rejections: {dict(rejections)}")
    for name in ("all_vintages", "current_grid_2025_plus"):
        m = report[name]
        assert isinstance(m, dict)
        print(
            f"{name}: n={m['n']} | exact {m['exact_agreement']:.1%}"
            f" | within one level {m['within_one_level']:.1%}"
        )
        confusion = m["confusion_matrix_obs_rows_pred_cols"]
        assert isinstance(confusion, dict)
        for obs in LEVELS:
            print(f"  obs {obs:>12}: {confusion[obs]}")
    print(f"report -> {args.out}")


if __name__ == "__main__":
    main()
