"""Download a stratified sample of the ADEME DPE database (single-family houses).

Dataset: « DPE Logements existants (depuis juillet 2021) », data.ademe.fr,
data-fair API ``datasets/dpe03existant`` (verified 2026-07-04; ~15.1 M rows,
Licence Ouverte v2.0). Raw data is NEVER committed (CLAUDE.md rule 6): output
goes to ``data/dpe_sample.jsonl`` which is gitignored.

Sampling: stratified by construction period x climate zone x main heating
energy, taking up to ``--per-stratum`` rows per stratum in dataset order.
This is deterministic but not random within a stratum — acceptable for a
validation of physical consistency, documented as a limitation in the report.

Usage: python validation/download_dpe.py [--per-stratum 30] [--out data/dpe_sample.jsonl]
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

API_BASE = "https://data.ademe.fr/data-fair/api/v1/datasets/dpe03existant/lines"

SELECT_COLUMNS = [
    "numero_dpe",
    "date_etablissement_dpe",
    "methode_application_dpe",
    "etiquette_dpe",
    "etiquette_ges",
    "conso_5_usages_par_m2_ep",
    "conso_5_usages_par_m2_ef",
    "emission_ges_5_usages_par_m2",
    "type_batiment",
    "periode_construction",
    "annee_construction",
    "surface_habitable_logement",
    "zone_climatique",
    "classe_altitude",
    "nombre_niveau_logement",
    "hauteur_sous_plafond",
    "qualite_isolation_murs",
    "qualite_isolation_plancher_bas",
    "qualite_isolation_plancher_haut_comble_perdu",
    "qualite_isolation_plancher_haut_comble_amenage",
    "qualite_isolation_plancher_haut_toit_terrasse",
    "qualite_isolation_menuiseries",
    "type_energie_principale_chauffage",
    "type_generateur_chauffage_principal",
    "type_energie_principale_ecs",
    "type_generateur_chauffage_principal_ecs",
    "type_ventilation",
    "deperditions_enveloppe",
    "besoin_chauffage",
    "besoin_ecs",
    "ubat_w_par_m2_k",
]

PERIODS = [
    "avant 1948",
    "1948-1974",
    "1975-1977",
    "1978-1982",
    "1983-1988",
    "1989-2000",
    "2001-2005",
    "2006-2012",
    "2013-2021",
    "après 2021",
]
ZONES = ["H1a", "H1b", "H1c", "H2a", "H2b", "H2c", "H2d", "H3"]
ENERGIES = [
    "Électricité",
    "Gaz naturel",
    "Fioul domestique",
    "Bois – Bûches",  # noqa: RUF001 - exact ADEME field value (en dash)
    "Bois – Granulés (pellets) ou briquettes",  # noqa: RUF001 - exact ADEME field value
]


def fetch_stratum(period: str, zone: str, energy: str, size: int) -> list[dict[str, object]]:
    """Fetch up to ``size`` house rows for one stratum."""
    qs = (
        f'type_batiment:maison AND periode_construction:"{period}" '
        f'AND zone_climatique:"{zone}" '
        f'AND type_energie_principale_chauffage:"{energy}"'
    )
    params = urllib.parse.urlencode(
        {"size": str(size), "qs": qs, "select": ",".join(SELECT_COLUMNS)}
    )
    url = f"{API_BASE}?{params}"
    request = urllib.request.Request(url, headers={"User-Agent": "renosim-validation/0.3"})
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))
    results: list[dict[str, object]] = payload.get("results", [])
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--per-stratum", type=int, default=30)
    parser.add_argument("--out", type=Path, default=Path("data/dpe_sample.jsonl"))
    args = parser.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    seen: set[str] = set()
    with args.out.open("w", encoding="utf-8") as out:
        for period in PERIODS:
            for zone in ZONES:
                for energy in ENERGIES:
                    try:
                        rows = fetch_stratum(period, zone, energy, args.per_stratum)
                    except Exception as exc:
                        print(f"WARN {period}/{zone}/{energy}: {exc}")
                        time.sleep(2)
                        continue
                    kept = 0
                    for row in rows:
                        key = str(row.get("numero_dpe") or id(row))
                        if key in seen:
                            continue
                        seen.add(key)
                        out.write(json.dumps(row, ensure_ascii=False) + "\n")
                        kept += 1
                    total += kept
                    time.sleep(0.15)  # stay well under the 10 req/s API limit
            print(f"{period}: cumulative rows = {total}")
    print(f"DONE: {total} rows -> {args.out}")


if __name__ == "__main__":
    main()
