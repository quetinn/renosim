"""Map ADEME DPE rows onto renosim Building objects.

This is the most delicate part of the validation (CLAUDE.md §7.2): ADEME fields
are heterogeneous and partially filled. Every mapping choice is documented here;
rejections carry an explicit reason so rejection rates can be reported.

Key mapping choices (summarised in the validation note):

M-1  Geometry is reconstructed, not read: the dataset gives no envelope areas.
     Assumption: square footprint of ``Sh / levels``, walls = perimeter x
     ceiling height x levels minus windows, roof = floor = footprint, window
     area = Sh / 6 (historical DPE convention for unknown glazing area).
M-2  Insulation quality labels select the U-value: "insuffisante" -> uninsulated
     defaults for pre-1975 constructions, but the period row for 1975+ ones
     (regulatory insulation existed; the DPE "insuffisante" class starts around
     U > 0.65, which covers the 1975-1988 period rows — treating them as fully
     uninsulated caused a +170 kWhep/m2 bias in calibration iteration 1);
     "moyenne" -> period row; "bonne" -> at least the 1989-2000 row;
     "très bonne" -> at least the post-2013 row. Only official table values
     are used, never invented ones.
M-3  Windows: "insuffisante" -> single glazing, "moyenne" -> old double,
     "bonne" -> recent double, "très bonne" -> low-e double.
M-4  Generator age parsed from the generator label when it embeds a period
     (e.g. "Chaudière gaz à condensation 2001-2015" -> midpoint), else from the
     construction year; reference year 2023 (median DPE vintage of the sample).
M-5  Wood log heating maps onto WOOD_BOILER and is evaluated with the pellet
     efficiency brackets (engine V1 limitation) — analysed separately.
M-6  (calibration iteration 3) A missing insulation-quality field means missing
     DATA, not an uninsulated wall: mapped to "moyenne". Fully uninsulated
     pre-1975 walls use U = 2.0 (mid-range of the official Umur0 table for
     traditional walls — pierre 40-55 cm: 2.05-2.3, briques pleines >= 34 cm:
     <= 1.65 — rather than the 2.5 cap which assumes the worst masonry).
M-7  (calibration iteration 4) Ground floors: houses overwhelmingly sit on a
     terre-plein or vide sanitaire, for which the 3CL replaces Upb by the much
     smaller Ue (ground buffering; annexe 1 §3.2.2, table p.18). We encode the
     official Ue row for 2S/P = 5 (typical house footprint/perimeter ratio) via
     the element's b coefficient: b = Ue(Upb)/Upb, clamped to [0.15, 1].
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

from renosim.models import (
    AltitudeClass,
    Building,
    ClimateZone,
    ConstructionPeriod,
    DHWGeneratorType,
    DHWSystem,
    EnergyCarrier,
    HeatingGeneratorType,
    HeatingSystem,
    OpaqueEnvelopeElement,
    VentilationSystem,
    VentilationType,
    Window,
)
from renosim.tables_io import load_table

REFERENCE_YEAR = 2023

_PERIOD_MAP = {
    "avant 1948": ConstructionPeriod.BEFORE_1948,
    "1948-1974": ConstructionPeriod.Y1948_1974,
    "1975-1977": ConstructionPeriod.Y1975_1977,
    "1978-1982": ConstructionPeriod.Y1978_1982,
    "1983-1988": ConstructionPeriod.Y1983_1988,
    "1989-2000": ConstructionPeriod.Y1989_2000,
    "2001-2005": ConstructionPeriod.Y2001_2005,
    "2006-2012": ConstructionPeriod.Y2006_2012,
    "2013-2021": ConstructionPeriod.AFTER_2013,
    "après 2021": ConstructionPeriod.AFTER_2013,
}

_ZONE_MAP = {z.value: z for z in ClimateZone}

_ALTITUDE_MAP = {
    "inférieur à 400m": AltitudeClass.LOW,
    "400-800m": AltitudeClass.MEDIUM,
    "supérieur à 800m": AltitudeClass.HIGH,
}

_ZONE_GROUP = {
    "H1a": "H1",
    "H1b": "H1",
    "H1c": "H1",
    "H2a": "H2",
    "H2b": "H2",
    "H2c": "H2",
    "H2d": "H2",
    "H3": "H3",
}

_PERIOD_KEY = {
    ConstructionPeriod.BEFORE_1948: "before_1948",
    ConstructionPeriod.Y1948_1974: "1948_1974",
    ConstructionPeriod.Y1975_1977: "1975_1977",
    ConstructionPeriod.Y1978_1982: "1978_1982",
    ConstructionPeriod.Y1983_1988: "1983_1988",
    ConstructionPeriod.Y1989_2000: "1989_2000",
    ConstructionPeriod.Y2001_2005: "2001_2005",
    ConstructionPeriod.Y2006_2012: "2006_2012",
    ConstructionPeriod.AFTER_2013: "after_2013",
}

_PERIOD_ORDER = list(_PERIOD_KEY)

_GLAZING_BY_QUALITY = {
    "insuffisante": "single_glazing",
    "moyenne": "double_glazing_old",
    "bonne": "double_glazing_recent",
    "très bonne": "double_glazing_low_e",
}


# Official Ue values for floors on terre-plein/vide sanitaire, annexe 1 p.18,
# row 2S/P = 5 (typical detached house): columns are Upb values.
_UE_UPB = [3.33, 1.43, 0.83, 0.45, 0.41, 0.37, 0.34, 0.31]
_UE_VAL = [0.38, 0.36, 0.34, 0.32, 0.30, 0.28, 0.26, 0.25]


def _ground_floor_b(upb: float) -> float:
    """Choice M-7: b = Ue/Upb from the official ground-contact table."""
    if upb >= _UE_UPB[0]:
        ue = _UE_VAL[0]
    elif upb <= _UE_UPB[-1]:
        ue = _UE_VAL[-1]
    else:
        ue = _UE_VAL[0]
        for (u1, e1), (u2, e2) in zip(
            zip(_UE_UPB, _UE_VAL, strict=True),
            zip(_UE_UPB[1:], _UE_VAL[1:], strict=True),
            strict=False,
        ):
            if u2 <= upb <= u1:
                ue = e2 + (e1 - e2) * (upb - u2) / (u1 - u2)
                break
    return min(1.0, max(0.15, ue / upb))


@dataclass(frozen=True)
class MappingResult:
    """Either a mapped building or a rejection reason."""

    building: Building | None
    reason: str | None
    observed_cep: float | None = None
    observed_label: str | None = None
    observed_ges: float | None = None
    stratum: tuple[str, str, str] | None = None
    #: "dpe_2021" (electricity EP factor 2.3) or "dpe_2026" (1.9), selected from
    #: the DPE issue date — the arrete du 13/08/2025 changed the factor on
    #: 2026-01-01, and the dataset mixes both vintages (see deviation D-13).
    regulation_vintage: str = "dpe_2021"


def _opaque_u(
    quality: str | None, period: ConstructionPeriod, zone: str, joule: bool, element: str
) -> float:
    """Choice M-2: U from insulation-quality label + official tables only."""
    table = load_table("u_values_default")
    heat = "joule" if joule else "others"
    group = _ZONE_GROUP[zone]

    def tab(p: ConstructionPeriod) -> float:
        key = _PERIOD_KEY[p]
        if p in (ConstructionPeriod.BEFORE_1948, ConstructionPeriod.Y1948_1974):
            key = "1975_1977"
        if element == "wall":
            return float(table["wall_insulated_by_period"][group][heat][key])
        if element == "roof":
            return float(table["roof_insulated_by_period"]["combles"][group][heat][key])
        return float(table["floor_insulated_by_period"][group][heat][key])

    uninsulated = {
        "wall": 2.0,  # M-6: mid-range official Umur0 for traditional walls
        "roof": float(table["uninsulated_defaults"]["roof_u0"]),
        "floor": float(table["uninsulated_defaults"]["floor_u0"]),
    }[element]

    if quality is None:
        quality = "moyenne"  # M-6: missing data, assume median state
    if quality == "insuffisante":
        if period in (ConstructionPeriod.BEFORE_1948, ConstructionPeriod.Y1948_1974):
            return uninsulated
        return tab(period)  # 1975+: regulatory insulation of the period
    if quality == "moyenne":
        return tab(period)
    if quality == "bonne":
        floor_p = max(period, ConstructionPeriod.Y1989_2000, key=_PERIOD_ORDER.index)
        return tab(floor_p)
    # très bonne
    return tab(ConstructionPeriod.AFTER_2013)


def _parse_generator_age(label: str | None, construction_year: int) -> float:
    """Choice M-4: age from the period embedded in the generator label."""
    if label:
        years = [int(y) for y in re.findall(r"(19\d{2}|20\d{2})", label)]
        if years:
            return max(0.0, REFERENCE_YEAR - sum(years) / len(years))
        m = re.search(r"avant (\d{4})", label.lower())
        if m:
            return max(0.0, REFERENCE_YEAR - (int(m.group(1)) - 5))
    return max(0.0, REFERENCE_YEAR - construction_year)


def _heating_system(row: dict[str, object], construction_year: int) -> HeatingSystem | None:
    energy = str(row.get("type_energie_principale_chauffage") or "")
    label = str(row.get("type_generateur_chauffage_principal") or "")
    low = label.lower()
    age = _parse_generator_age(label, construction_year)

    if energy == "Électricité":
        if "pac" in low or "pompe" in low:
            gen = (
                HeatingGeneratorType.HEAT_PUMP_AIR_AIR
                if "air/air" in low
                else HeatingGeneratorType.HEAT_PUMP_AIR_WATER
            )
            return HeatingSystem(gen, EnergyCarrier.ELECTRICITY, age)
        return HeatingSystem(HeatingGeneratorType.ELECTRIC_JOULE, EnergyCarrier.ELECTRICITY, age)
    if energy == "Gaz naturel":
        if "condensation" in low:
            gen = HeatingGeneratorType.CONDENSING_BOILER
        elif "basse température" in low:
            gen = HeatingGeneratorType.LOW_TEMPERATURE_BOILER
        else:
            gen = HeatingGeneratorType.STANDARD_BOILER
        return HeatingSystem(gen, EnergyCarrier.NATURAL_GAS, age)
    if energy == "Fioul domestique":
        if "condensation" in low:
            gen = HeatingGeneratorType.CONDENSING_BOILER
        else:
            gen = HeatingGeneratorType.STANDARD_BOILER
        return HeatingSystem(gen, EnergyCarrier.FUEL_OIL, age)
    if energy.startswith("Bois"):
        pellets = "granulé" in energy.lower() or "granulé" in low
        carrier = EnergyCarrier.WOOD_PELLETS if pellets else EnergyCarrier.WOOD_LOGS
        gen = (
            HeatingGeneratorType.WOOD_PELLET_STOVE if pellets else HeatingGeneratorType.WOOD_BOILER
        )
        return HeatingSystem(gen, carrier, age)
    return None


def _dhw_system(row: dict[str, object], heating: HeatingSystem) -> DHWSystem:
    label = str(
        row.get("type_generateur_chauffage_principal_ecs")
        or row.get("type_generateur_n1_ecs_n1")
        or ""
    ).lower()
    energy = str(row.get("type_energie_principale_ecs") or "")
    if "thermodynamique" in label or "cet" in label.split():
        return DHWSystem(DHWGeneratorType.HEAT_PUMP_WATER_HEATER, EnergyCarrier.ELECTRICITY)
    if "ballon électrique" in label or (energy == "Électricité" and "chaudière" not in label):
        return DHWSystem(DHWGeneratorType.ELECTRIC_STORAGE, EnergyCarrier.ELECTRICITY)
    if "chauffe-eau gaz" in label:
        return DHWSystem(DHWGeneratorType.GAS_STORAGE_OR_INSTANT, EnergyCarrier.NATURAL_GAS)
    return DHWSystem(DHWGeneratorType.COUPLED_TO_HEATING_SYSTEM, heating.energy_carrier)


def _ventilation(row: dict[str, object]) -> VentilationSystem:
    label = str(row.get("type_ventilation") or "").lower()
    recent = "après 2012" in label
    if "hygro b" in label:
        vtype = VentilationType.EXHAUST_ONLY_HYGRO_B
    elif "hygro a" in label:
        vtype = VentilationType.EXHAUST_ONLY_HYGRO_A
    elif "double flux" in label or "vmc df" in label:
        vtype = VentilationType.BALANCED_HEAT_RECOVERY
    elif "vmc" in label:
        vtype = VentilationType.EXHAUST_ONLY_MANUAL
    else:
        vtype = VentilationType.NATURAL
    return VentilationSystem(ventilation_type=vtype, installed_after_2012=recent)


def _roof_quality(row: dict[str, object]) -> str | None:
    for key in (
        "qualite_isolation_plancher_haut_comble_perdu",
        "qualite_isolation_plancher_haut_comble_amenage",
        "qualite_isolation_plancher_haut_toit_terrasse",
    ):
        value = row.get(key)
        if value:
            return str(value)
    return None


def map_row(row: dict[str, object]) -> MappingResult:
    """Map one ADEME row onto a Building, or reject with a reason."""

    def reject(reason: str) -> MappingResult:
        return MappingResult(building=None, reason=reason)

    if str(row.get("methode_application_dpe") or "") != "dpe maison individuelle":
        return reject("methode_non_maison")
    label = row.get("etiquette_dpe")
    cep = row.get("conso_5_usages_par_m2_ep")
    if not label or cep is None:
        return reject("etiquette_ou_cep_manquante")
    sh_raw = row.get("surface_habitable_logement")
    if sh_raw is None:
        return reject("surface_manquante")
    sh = float(sh_raw)  # type: ignore[arg-type]
    if not 30.0 <= sh <= 400.0:
        return reject("surface_hors_bornes")

    period_label = str(row.get("periode_construction") or "")
    period = _PERIOD_MAP.get(period_label)
    if period is None:
        return reject("periode_inconnue")
    year_raw = row.get("annee_construction")
    construction_year = int(year_raw) if year_raw else 1900 + 60  # type: ignore[arg-type]

    zone = _ZONE_MAP.get(str(row.get("zone_climatique") or ""))
    if zone is None:
        return reject("zone_inconnue")
    altitude = _ALTITUDE_MAP.get(str(row.get("classe_altitude") or ""), AltitudeClass.LOW)

    heating = _heating_system(row, construction_year)
    if heating is None:
        return reject("chauffage_non_mappe")
    joule = heating.generator_type is HeatingGeneratorType.ELECTRIC_JOULE

    # Choice M-1: reconstructed geometry
    levels_raw = row.get("nombre_niveau_logement")
    levels = max(1, int(levels_raw)) if levels_raw else 1  # type: ignore[arg-type]
    hsp_raw = row.get("hauteur_sous_plafond")
    hsp = float(hsp_raw) if hsp_raw else 2.5  # type: ignore[arg-type]
    footprint = sh / levels
    perimeter = 4.0 * math.sqrt(footprint)
    window_area = sh / 6.0
    wall_area = max(10.0, perimeter * hsp * levels - window_area)

    wall_u = _opaque_u(
        str(row.get("qualite_isolation_murs") or "") or None, period, zone.value, joule, "wall"
    )
    floor_u = _opaque_u(
        str(row.get("qualite_isolation_plancher_bas") or "") or None,
        period,
        zone.value,
        joule,
        "floor",
    )
    roof_u = _opaque_u(_roof_quality(row), period, zone.value, joule, "roof")

    glazing_quality = str(row.get("qualite_isolation_menuiseries") or "moyenne")
    glazing_key = _GLAZING_BY_QUALITY.get(glazing_quality, "double_glazing_old")
    win = load_table("u_values_default")["window_defaults"][glazing_key]

    building = Building(
        living_area_m2=sh,
        construction_period=period,
        climate_zone=zone,
        altitude_class=altitude,
        walls=(OpaqueEnvelopeElement(area_m2=wall_area, u_value_w_per_m2k=wall_u),),
        roof=OpaqueEnvelopeElement(area_m2=footprint, u_value_w_per_m2k=roof_u),
        floor=OpaqueEnvelopeElement(
            area_m2=footprint,
            u_value_w_per_m2k=floor_u,
            unheated_space_reduction_coefficient=_ground_floor_b(floor_u),
        ),
        windows=(
            Window(
                area_m2=window_area,
                u_value_w_per_m2k=float(win["u_w_per_m2k"]),
                solar_factor=float(win["solar_factor"]),
            ),
        ),
        heating_system=heating,
        dhw_system=_dhw_system(row, heating),
        ventilation_system=_ventilation(row),
    )
    ges = row.get("emission_ges_5_usages_par_m2")
    dpe_date = str(row.get("date_etablissement_dpe") or "")
    vintage = "dpe_2026" if dpe_date >= "2026-01-01" else "dpe_2021"
    return MappingResult(
        building=building,
        reason=None,
        observed_cep=float(cep),  # type: ignore[arg-type]
        observed_label=str(label),
        observed_ges=float(ges) if ges is not None else None,  # type: ignore[arg-type]
        stratum=(
            period_label,
            zone.value,
            str(row.get("type_energie_principale_chauffage") or ""),
        ),
        regulation_vintage=vintage,
    )
