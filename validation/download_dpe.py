"""Download a stratified sample of the ADEME DPE database (houses or apartments).

Dataset: « DPE Logements existants (depuis juillet 2021) », data.ademe.fr,
data-fair API ``datasets/dpe03existant`` (verified 2026-07-04, columns
re-verified against the live schema on 2026-07-11; ~15.1 M rows, Licence
Ouverte v2.0). Raw data is NEVER committed (CLAUDE.md rule 6): output goes to
``data/*.jsonl`` which is gitignored.

Sampling: stratified by construction period x climate zone x main heating
energy, taking up to ``--per-stratum`` rows per stratum. By default rows come
in dataset order (deterministic, not random — the calibration samples
dpe_sample*.jsonl were drawn this way). ``--random`` uses the API's
reproducible pseudo-random order (``sort=_rand``) and ``--exclude`` drops every
``numero_dpe`` already present in the given files: this is how the independent
TEST sample is drawn (audit 2026-11-25 §3.4).

Usage:
    python validation/download_dpe.py [--per-stratum 30] [--out data/dpe_sample.jsonl]
    python validation/download_dpe.py --building-type appartement --out data/dpe_apartments.jsonl
    python validation/download_dpe.py --random --out data/dpe_test_v1.jsonl
        --exclude data/dpe_sample.jsonl data/dpe_sample_v2.jsonl
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
    "version_dpe",
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
    # v2 columns (2026-07-11): building inertia (engine input since #10), the
    # apartment position fields (#15) and the summer-comfort indicators (#16
    # proposal — downloaded now so a future campaign needs no re-download).
    "classe_inertie_batiment",
    # Detailed loss breakdown (apartment calibration, campaign v3):
    "deperditions_murs",
    "deperditions_planchers_hauts",
    "deperditions_planchers_bas",
    "deperditions_baies_vitrees",
    "deperditions_portes",
    "deperditions_ponts_thermiques",
    "deperditions_renouvellement_air",
    "type_installation_chauffage",
    "type_installation_ecs",
    "type_emetteur_installation_chauffage_n1",
    "position_logement_dans_immeuble",
    "numero_etage_appartement",
    "nombre_niveau_immeuble",
    "nombre_appartement",
    "surface_habitable_immeuble",
    "logement_traversant",
    "ventilation_posterieure_2012",
    "indicateur_confort_ete",
    "protection_solaire_exterieure",
    "presence_brasseur_air",
    "besoin_refroidissement",
    "conso_refroidissement_ep",
    "type_generateur_froid",
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


def fetch_stratum(
    period: str,
    zone: str,
    energy: str,
    size: int,
    building_type: str = "maison",
    sort: str | None = None,
    method_version: str | None = None,
) -> list[dict[str, object]]:
    """Fetch up to ``size`` rows of one building type for one stratum.

    ``method_version`` restricts the rows to one DPE method version
    (``version_dpe``, e.g. "2.6"), as required by the validation protocol
    announced in the note (§7).
    """
    qs = (
        f'type_batiment:{building_type} AND periode_construction:"{period}" '
        f'AND zone_climatique:"{zone}" '
        f'AND type_energie_principale_chauffage:"{energy}"'
    )
    if method_version is not None:
        qs += f' AND version_dpe:"{method_version}"'
    query = {"size": str(size), "qs": qs, "select": ",".join(SELECT_COLUMNS)}
    if sort is not None:
        query["sort"] = sort
    params = urllib.parse.urlencode(query)
    url = f"{API_BASE}?{params}"
    request = urllib.request.Request(url, headers={"User-Agent": "renosim-validation/0.4"})
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))
    results: list[dict[str, object]] = payload.get("results", [])
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--per-stratum", type=int, default=30)
    parser.add_argument("--out", type=Path, default=Path("data/dpe_sample.jsonl"))
    parser.add_argument("--building-type", choices=["maison", "appartement"], default="maison")
    parser.add_argument(
        "--random", action="store_true", help="reproducible pseudo-random order (sort=_rand)"
    )
    parser.add_argument(
        "--exclude", type=Path, nargs="*", default=[], help="JSONL files whose DPE to skip"
    )
    parser.add_argument(
        "--method-version",
        default=None,
        help='keep only one DPE method version (field version_dpe, e.g. "2.6")',
    )
    args = parser.parse_args()

    excluded: set[str] = set()
    for path in args.exclude:
        with path.open(encoding="utf-8") as f:
            excluded.update(str(json.loads(line).get("numero_dpe")) for line in f if line.strip())
    print(f"excluded DPE ids: {len(excluded)}")
    sort = "_rand" if args.random else None
    # Over-fetch when excluding so each stratum can still be filled.
    fetch_size = args.per_stratum * 2 if excluded else args.per_stratum

    args.out.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    seen: set[str] = set(excluded)
    with args.out.open("w", encoding="utf-8") as out:
        for period in PERIODS:
            for zone in ZONES:
                for energy in ENERGIES:
                    try:
                        rows = fetch_stratum(
                            period,
                            zone,
                            energy,
                            fetch_size,
                            args.building_type,
                            sort,
                            args.method_version,
                        )
                    except Exception as exc:
                        print(f"WARN {period}/{zone}/{energy}: {exc}")
                        time.sleep(2)
                        continue
                    kept = 0
                    for row in rows:
                        if kept >= args.per_stratum:
                            break
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
