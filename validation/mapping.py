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
M-5  Wood heating (revised 2026-11-27, v1.1). The generator label decides:
     a log stove, insert, closed fireplace or cooker ("Poêle bûche", "insert",
     "Foyer fermé", "Cuisinière") maps onto WOOD_LOG_STOVE (official §13.1
     efficiencies, period from the label, M-4); a pellet stove onto
     WOOD_PELLET_STOVE; a "Chaudière bois bûche/granulés" label onto
     WOOD_BOILER (official §13.2.2.3 efficiencies, pellet or log rows by fuel).
     Anything else, including a missing label (~40 % of the wood rows), keeps
     the former efficiency proxy, now explicit in the mapping: pellet-stove
     efficiencies with the carrier of the fuel (D-22). Those rows behave in the
     DPE neither like labelled stoves nor like boilers (consumption/need 1.14-
     1.17 vs 1.46-1.48), so no official row is assumed for them. Known gap: ~23 % of
     the wood rows of the calibration sample carry a HEAT-PUMP main generator
     label with wood as the main energy: see M-12.
M-12 (2026-11-27, v1.1) Wood as main energy with a HEAT-PUMP main generator label
     is a heat pump with a wood stove/insert back-up (3CL §9.3: 75 % / 25 %
     of the need; the stove's lower efficiency makes wood the main energy in
     final energy). Mapped onto the heat pump + heating_backup
     (log stove for wood-log energy, pellet stove for pellets), back-up age
     unknown (middle bracket). Joule-emitter labels are left as wood-heated
     (bathroom heater, §9.4-9.5): measured on the calibration sample, treating
     them as electric main systems gave mixed results (n ~ 60).
M-13 (2026-11-27, v1.1) Linear thermal bridges (3CL §3.4, houses only): exposed
     perimeter, levels and window area of the M-1 geometry; an element counts
     as insulated unless its quality is "insuffisante" before 1975 (same rule
     as its U-value, M-2/M-6), layouts by the official defaults (walls ITI,
     roof and floor ITE); heavy elements from classe_inertie_batiment:
     "Légère" -> light walls and floor (no wall junction counted), "Très
     lourde" -> heavy top floor too, otherwise heavy walls and floor, light
     top floor (§7 defaults). Apartments keep the calibrated flat surcharge.
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
M-8  (campaign v3, 2026-07-11) Building inertia: the ADEME field
     ``classe_inertie_batiment`` maps onto InertiaClass (Légère -> light,
     Moyenne -> medium, Lourde/Très lourde -> heavy, missing -> unknown =
     medium), feeding both the utilization-factor exponent and the I0 column.
M-9  (campaign v3) Apartments: only ``dpe appartement individuel`` rows are
     kept (building-generated and RT2012-study DPEs are rejected — different
     input pedigree). Geometry mirrors the app bridge (D-18): square footprint
     of Sh, one level; ``logement_traversant`` selects 2 opposite exposed
     facades (50 % of the perimeter) vs 1 exposed + 1 on the common
     circulation (official b = 0.35); ``position_logement_dans_immeuble``
     drives the ceiling/floor adjacency (b = 0 to heated dwellings; RDC uses
     the M-7 ground treatment; missing position -> intermediate).
M-10 (#16 brique 1) Summer-comfort fields: ``protection_solaire_exterieure``
     is the official binary "all S/E/W/roof bays protected" flag -> FULL/NONE
     (missing -> UNKNOWN, treated as FULL); ``presence_brasseur_air`` -> fixed
     fans; ``logement_traversant`` -> through_dwelling (houses included;
     missing -> engine default: through). Roof state: annexe 9 tests the
     PRESENCE of roof insulation, while the ADEME quality label rates its
     U-value — "moyenne"/"bonne"/"très bonne" imply an insulated roof, but
     "insuffisante" is ambiguous (uninsulated, or insulated but poorly), so it
     falls back — like a missing label — to the official annexe 9 pre/post-1975
     default (mapping "insuffisante" to "not insulated" cost 5.5 points of
     exact agreement on the 2025+ sub-sample: 90.0 % vs 95.5 %).
M-11 (#16 brique 2) Cooling: a non-empty ``type_generateur_froid`` declares an
     air conditioner; the installation period embedded in the label ("avant
     2008", "entre 2008 et 2014", "à partir de 2015" / "entre 2015 et 2016" /
     "après 2017") selects the SEER bracket; "autre système..." labels map to
     the unknown period (recent bracket, D-20).
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import date

from renosim.envelope import default_insulation_layout
from renosim.models import (
    AltitudeClass,
    Building,
    ClimateZone,
    ConstructionPeriod,
    CoolingPeriod,
    DHWGeneratorType,
    DHWSystem,
    DwellingType,
    EnergyCarrier,
    HeatingGeneratorType,
    HeatingSystem,
    InertiaClass,
    OpaqueEnvelopeElement,
    SolarProtectionLevel,
    ThermalBridgeInputs,
    VentilationSystem,
    VentilationType,
    Window,
)
from renosim.outputs import regulation_vintage_in_force
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

#: M-8: ADEME classe_inertie_batiment -> engine InertiaClass.
_INERTIA_MAP = {
    "Légère": InertiaClass.LIGHT,
    "Moyenne": InertiaClass.MEDIUM,
    "Lourde": InertiaClass.HEAVY,
    "Très lourde": InertiaClass.HEAVY,
}

#: M-9: ADEME position_logement_dans_immeuble -> internal position keys.
_POSITION_MAP = {
    "RDC": "ground",
    "étage intermédiaire": "intermediate",
    "dernier étage": "top",
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
    #: "dpe_2021" (2.3), "dpe_2026" (1.9) or "dpe_2027" (1.7), the convention in
    #: force on the DPE issue date (the dataset mixes vintages, deviation D-13).
    regulation_vintage: str = "dpe_2021"
    #: Year of the DPE issue date (``date_etablissement_dpe``), for the
    #: by-year breakdown of the validation report.
    dpe_year: str | None = None


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


#: Generator labels of wood-log stoves and inserts (3CL §13.1 rows), choice M-5.
_LOG_STOVE_KEYWORDS = ("poêle bûche", "insert", "foyer fermé", "cuisinière")


#: Heat-pump main-generator labels, choice M-12. Joule emitters are excluded:
#: with wood as the main energy they are usually the bathroom heater of a
#: wood-heated house (3CL §9.4-9.5), not a main system with a wood back-up.
_HEAT_PUMP_KEYWORDS = ("pac ", "pompe à chaleur")


def _wood_with_electric_main(row: dict[str, object]) -> bool:
    """Choice M-12: wood main energy but a heat-pump main generator label."""
    energy = str(row.get("type_energie_principale_chauffage") or "")
    low = str(row.get("type_generateur_chauffage_principal") or "").lower() + " "
    return energy.startswith("Bois") and any(k in low for k in _HEAT_PUMP_KEYWORDS)


def _heating_backup(row: dict[str, object]) -> HeatingSystem | None:
    """Choice M-12: the wood stove/insert back-up of an electric main system."""
    if not _wood_with_electric_main(row):
        return None
    energy = str(row.get("type_energie_principale_chauffage") or "").lower()
    if "granulé" in energy:
        return HeatingSystem(HeatingGeneratorType.WOOD_PELLET_STOVE, EnergyCarrier.WOOD_PELLETS)
    return HeatingSystem(HeatingGeneratorType.WOOD_LOG_STOVE, EnergyCarrier.WOOD_LOGS)


def _heating_system(row: dict[str, object], construction_year: int) -> HeatingSystem | None:
    energy = str(row.get("type_energie_principale_chauffage") or "")
    label = str(row.get("type_generateur_chauffage_principal") or "")
    low = label.lower()
    age = _parse_generator_age(label, construction_year)
    if _wood_with_electric_main(row):
        energy = "Électricité"  # main system; the wood part is the back-up (M-12)

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
        if "chaudière bois" in low:
            gen = HeatingGeneratorType.WOOD_BOILER  # official §13.2.2.3 rows
        elif not pellets and any(k in low for k in _LOG_STOVE_KEYWORDS):
            gen = HeatingGeneratorType.WOOD_LOG_STOVE
        else:
            # Pellet stoves, and the efficiency proxy kept for missing or other
            # labels (M-5): pellet-stove efficiencies, carrier of the fuel.
            gen = HeatingGeneratorType.WOOD_PELLET_STOVE
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

    methode = str(row.get("methode_application_dpe") or "")
    if methode == "dpe maison individuelle":
        dwelling = DwellingType.HOUSE
    elif methode == "dpe appartement individuel":
        dwelling = DwellingType.APARTMENT  # M-9
    else:
        # Building-generated apartment DPEs and RT2012-study DPEs have a
        # different input pedigree; they are rejected rather than mapped.
        return reject("methode_non_supportee")
    label = row.get("etiquette_dpe")
    cep = row.get("conso_5_usages_par_m2_ep")
    if not label or cep is None:
        return reject("etiquette_ou_cep_manquante")
    sh_raw = row.get("surface_habitable_logement")
    if sh_raw is None:
        return reject("surface_manquante")
    sh = float(sh_raw)  # type: ignore[arg-type]
    low_bound, high_bound = (15.0, 200.0) if dwelling is DwellingType.APARTMENT else (30.0, 400.0)
    if not low_bound <= sh <= high_bound:
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

    # Choice M-1 (houses) / M-9 (apartments): reconstructed geometry
    levels_raw = row.get("nombre_niveau_logement")
    levels = max(1, int(levels_raw)) if levels_raw else 1  # type: ignore[arg-type]
    if dwelling is DwellingType.APARTMENT:
        levels = 1
    hsp_raw = row.get("hauteur_sous_plafond")
    hsp = float(hsp_raw) if hsp_raw else 2.5  # type: ignore[arg-type]
    footprint = sh / levels
    full_perimeter = 4.0 * math.sqrt(footprint)
    traversant_raw = row.get("logement_traversant")
    declared_through = bool(int(traversant_raw)) if traversant_raw is not None else None  # type: ignore[arg-type]
    if dwelling is DwellingType.APARTMENT:
        traversant = declared_through if declared_through is not None else True
        perimeter = full_perimeter * (0.5 if traversant else 0.25)
    else:
        traversant = True
        perimeter = full_perimeter
    window_area = sh * float(load_table("conventions")["geometry"]["window_area_fraction"]["value"])
    min_wall = 10.0 if dwelling is DwellingType.HOUSE else 5.0
    wall_area = max(min_wall, perimeter * hsp * levels - window_area)
    if dwelling is DwellingType.APARTMENT:
        # M-9: calibrated deperditive-wall factor (see apartment_reconstruction).
        wall_area *= float(
            load_table("u_values_default")["apartment_reconstruction"]["wall_area_factor"]
        )

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

    # M-8: building inertia from the ADEME field (missing -> medium behaviour).
    inertia = _INERTIA_MAP.get(str(row.get("classe_inertie_batiment") or ""), InertiaClass.UNKNOWN)

    # M-10 (#16 brique 1): summer-comfort inputs.
    protection_raw = row.get("protection_solaire_exterieure")
    if protection_raw is None:
        protections = SolarProtectionLevel.UNKNOWN
    elif int(protection_raw):  # type: ignore[arg-type]
        protections = SolarProtectionLevel.FULL
    else:
        protections = SolarProtectionLevel.NONE
    fans_raw = row.get("presence_brasseur_air")
    fans = bool(int(fans_raw)) if fans_raw is not None else False  # type: ignore[arg-type]
    roof_quality = _roof_quality(row)
    # "insuffisante" is ambiguous for the annexe 9 presence test -> official
    # period default, like a missing label (see M-10).
    roof_insulated = True if roof_quality not in (None, "insuffisante") else None

    # M-11: air conditioner and its SEER bracket from type_generateur_froid.
    froid_label = str(row.get("type_generateur_froid") or "").lower()
    has_ac = bool(froid_label)
    if "avant 2008" in froid_label:
        ac_period = CoolingPeriod.BEFORE_2008
    elif "2008" in froid_label:
        ac_period = CoolingPeriod.Y2008_2014
    elif "2015" in froid_label or "2017" in froid_label:
        ac_period = CoolingPeriod.FROM_2015
    else:
        ac_period = CoolingPeriod.UNKNOWN

    walls: list[OpaqueEnvelopeElement] = [
        OpaqueEnvelopeElement(area_m2=wall_area, u_value_w_per_m2k=wall_u)
    ]
    if dwelling is DwellingType.APARTMENT:
        # M-9: position from the dedicated field, else floor number 0 -> RDC,
        # else the calibrated expected-value b for an unknown position.
        position = _POSITION_MAP.get(str(row.get("position_logement_dans_immeuble") or ""), "")
        etage_raw = row.get("numero_etage_appartement")
        if not position and etage_raw is not None and int(etage_raw) == 0:  # type: ignore[arg-type]
            position = "ground"
        recon = load_table("u_values_default")["apartment_reconstruction"]
        if position == "top":
            roof_b = 1.0
        elif position == "":
            roof_b = float(recon["unknown_position_roof_b"])
        else:
            roof_b = 0.0
        if position == "ground":
            floor_b = _ground_floor_b(floor_u)
        elif position == "":
            floor_b = float(recon["unknown_position_floor_b"])
        else:
            floor_b = 0.0
        if not traversant:
            circulation_b = float(load_table("u_values_default")["wall_b_common_circulation"]["b"])
            walls.append(
                OpaqueEnvelopeElement(
                    area_m2=0.25 * full_perimeter * hsp,
                    u_value_w_per_m2k=wall_u,
                    unheated_space_reduction_coefficient=circulation_b,
                )
            )
    else:
        roof_b = 1.0
        floor_b = _ground_floor_b(floor_u)

    # M-13: linear thermal bridges for houses (3CL §3.4).
    thermal_bridges: ThermalBridgeInputs | None = None
    if dwelling is DwellingType.HOUSE:
        inertia_label = str(row.get("classe_inertie_batiment") or "")

        def _insulated(quality: str | None) -> bool:
            early = period in (ConstructionPeriod.BEFORE_1948, ConstructionPeriod.Y1948_1974)
            return not (quality == "insuffisante" and early)

        thermal_bridges = ThermalBridgeInputs(
            exposed_perimeter_m=perimeter,
            levels=levels,
            window_area_m2=window_area,
            wall_insulation=default_insulation_layout(
                "wall", _insulated(str(row.get("qualite_isolation_murs") or "") or None), period
            ),
            floor_insulation=default_insulation_layout(
                "floor",
                _insulated(str(row.get("qualite_isolation_plancher_bas") or "") or None),
                period,
            ),
            roof_insulation=default_insulation_layout(
                "roof", _insulated(_roof_quality(row)), period
            ),
            heavy_walls=inertia_label != "Légère",
            heavy_floor=inertia_label != "Légère",
            heavy_ceiling=inertia_label == "Très lourde",
        )

    building = Building(
        living_area_m2=sh,
        thermal_bridge_inputs=thermal_bridges,
        construction_period=period,
        climate_zone=zone,
        altitude_class=altitude,
        walls=tuple(walls),
        roof=OpaqueEnvelopeElement(
            area_m2=footprint,
            u_value_w_per_m2k=roof_u,
            unheated_space_reduction_coefficient=roof_b,
        ),
        floor=OpaqueEnvelopeElement(
            area_m2=footprint,
            u_value_w_per_m2k=floor_u,
            unheated_space_reduction_coefficient=floor_b,
        ),
        windows=(
            Window(
                area_m2=window_area,
                u_value_w_per_m2k=float(win["u_w_per_m2k"]),
                solar_factor=float(win["solar_factor"]),
            ),
        ),
        heating_system=heating,
        heating_backup=_heating_backup(row),
        dhw_system=_dhw_system(row, heating),
        ventilation_system=_ventilation(row),
        inertia=inertia,
        dwelling_type=dwelling,
        single_exposed_facade=dwelling is DwellingType.APARTMENT and not traversant,
        exterior_solar_protections=protections,
        has_fixed_air_circulators=fans,
        has_air_conditioning=has_ac,
        air_conditioning_period=ac_period,
        roof_insulated=roof_insulated,
        through_dwelling=(traversant if dwelling is DwellingType.APARTMENT else declared_through),
    )
    ges = row.get("emission_ges_5_usages_par_m2")
    dpe_date = str(row.get("date_etablissement_dpe") or "")
    vintage = (
        regulation_vintage_in_force(date.fromisoformat(dpe_date[:10])) if dpe_date else "dpe_2021"
    )
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
        dpe_year=dpe_date[:4] or None,
    )
