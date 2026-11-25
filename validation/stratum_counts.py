"""Count the ADEME DPE population per sampling stratum (for post-stratification).

The validation samples are stratified and *balanced* (same quota per
construction period x climate zone x heating energy), so their raw metrics
over-represent rare strata (e.g. wood-pellet houses in H3). This script asks
the ADEME API for the number of DPE in each stratum (``size=0``, the ``total``
field only — no row is downloaded) so that run_validation.py can reweight the
metrics to the DPE population (audit 2026-11-25 §3.4).

The counts are aggregates of open data (Licence Ouverte v2.0), small and
derived, so the output file is committed under validation/report/.

Usage:
    python validation/stratum_counts.py [--out validation/report/stratum_counts_maisons.json]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from download_dpe import API_BASE, ENERGIES, PERIODS, ZONES


def count_stratum(period: str, zone: str, energy: str, building_type: str) -> int:
    """Number of DPE lines matching one stratum (API ``total``)."""
    qs = (
        f'type_batiment:{building_type} AND periode_construction:"{period}" '
        f'AND zone_climatique:"{zone}" '
        f'AND type_energie_principale_chauffage:"{energy}"'
    )
    params = urllib.parse.urlencode({"size": "0", "qs": qs})
    request = urllib.request.Request(
        f"{API_BASE}?{params}", headers={"User-Agent": "renosim-validation/0.4"}
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return int(payload["total"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out", type=Path, default=Path("validation/report/stratum_counts_maisons.json")
    )
    parser.add_argument("--building-type", choices=["maison", "appartement"], default="maison")
    args = parser.parse_args()

    counts: dict[str, int] = {}
    for period in PERIODS:
        for zone in ZONES:
            for energy in ENERGIES:
                for attempt in range(3):
                    try:
                        counts[f"{period}|{zone}|{energy}"] = count_stratum(
                            period, zone, energy, args.building_type
                        )
                        break
                    except Exception as exc:  # network hiccup: retry twice
                        print(f"WARN {period}/{zone}/{energy} (try {attempt + 1}): {exc}")
                        time.sleep(2)
                time.sleep(0.15)
        print(f"{period}: done")

    report = {
        "_meta": {
            "description": "Number of DPE per stratum (construction period x climate zone x "
            "main heating energy) in the ADEME dataset, for post-stratified validation metrics.",
            "dataset": "DPE Logements existants (depuis juillet 2021), data.ademe.fr, "
            "data-fair dataset dpe03existant (Licence Ouverte v2.0)",
            "building_type": args.building_type,
            "date_accessed": date.today().isoformat(),
            "key_format": "periode|zone|energie (exact ADEME field values)",
        },
        "total": sum(counts.values()),
        "counts": counts,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"DONE: {len(counts)} strata, {report['total']} DPE -> {args.out}")


if __name__ == "__main__":
    main()
