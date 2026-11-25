"""Fetch extra ADEME fields for the DPE of an existing sample (sidecar file).

Used to diagnose the 2022-2025 bias of campaign v5 (note de validation v2,
§5.2): method version, last modification date and the per-use consumptions in
final AND primary energy. For an all-electric use, the EP/EF ratio reveals the
primary-energy coefficient actually applied in the published DPE (2.3 or 1.9).

Rows are fetched by ``numero_dpe`` in batches; the output is a sidecar JSONL
(``<sample>.extra.jsonl``, gitignored with the rest of data/) keyed by
``numero_dpe``. Raw data is never committed (CLAUDE.md rule 6).

Usage:
    python validation/enrich_sample.py data/dpe_test_v1.jsonl [data/dpe_sample_v2.jsonl ...]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from download_dpe import API_BASE

EXTRA_COLUMNS = [
    "numero_dpe",
    "version_dpe",
    "modele_dpe",
    "date_derniere_modification_dpe",
    "conso_5_usages_ep",
    "conso_5_usages_ef",
    "conso_chauffage_ep",
    "conso_chauffage_ef",
    "conso_ecs_ep",
    "conso_ecs_ef",
    "conso_eclairage_ep",
    "conso_eclairage_ef",
    "conso_auxiliaires_ep",
    "conso_auxiliaires_ef",
    "conso_refroidissement_ep",
    "conso_refroidissement_ef",
    "type_energie_principale_ecs",
]

BATCH = 50


def fetch_batch(ids: list[str]) -> list[dict[str, object]]:
    """Fetch the extra columns for up to BATCH DPE numbers."""
    qs = "numero_dpe:(" + " OR ".join(f'"{i}"' for i in ids) + ")"
    params = urllib.parse.urlencode(
        {"size": str(len(ids)), "qs": qs, "select": ",".join(EXTRA_COLUMNS)}
    )
    request = urllib.request.Request(
        f"{API_BASE}?{params}", headers={"User-Agent": "renosim-validation/0.4"}
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))
    results: list[dict[str, object]] = payload.get("results", [])
    return results


def enrich(sample: Path) -> Path:
    ids = [
        str(json.loads(line)["numero_dpe"])
        for line in sample.open(encoding="utf-8")
        if line.strip()
    ]
    out = sample.with_suffix(".extra.jsonl")
    found = 0
    with out.open("w", encoding="utf-8") as f:
        for start in range(0, len(ids), BATCH):
            chunk = ids[start : start + BATCH]
            for attempt in range(3):
                try:
                    rows = fetch_batch(chunk)
                    break
                except Exception as exc:  # network hiccup: retry twice
                    print(f"WARN batch {start} (try {attempt + 1}): {exc}")
                    time.sleep(2)
            else:
                rows = []
            for row in rows:
                row.pop("_score", None)
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            found += len(rows)
            time.sleep(0.15)
    print(f"{sample}: {found}/{len(ids)} rows enriched -> {out}")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("samples", type=Path, nargs="+")
    args = parser.parse_args()
    for sample in args.samples:
        enrich(sample)


if __name__ == "__main__":
    main()
