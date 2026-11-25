"""JSON bridge between the web app (through Pyodide) and the engine.

The front end serialises the guided-form state to the versioned input schema
below and calls :func:`run_simulation`; it never re-implements any business
logic (CLAUDE.md §3.2). The bridge owns the *form -> Building* mapping: the
geometry reconstruction and U-value resolution reuse the conventions
calibrated during the Phase 3 ADEME campaign (choices M-1, M-6, M-7 in
``validation/mapping.py``), reading every business constant from ``tables/``.

Input schema (``schema_version`` = :data:`renosim.SCHEMA_VERSION`)::

    {
      "schema_version": "0.1",
      "regulation_vintage": "dpe_2027" | "dpe_2026" | "dpe_2021",  # optional: in force today
      "building": {
        "living_area_m2": 100.0,
        "levels": 1,                                         # optional
        "construction_period": "1948_1974",
        "climate_zone": "H1a",
        "altitude_class": "low",
        "dwelling_type": "house" | "apartment",              # optional (house)
        "apartment": {                                       # apartment only
            "position": "ground" | "intermediate" | "top" | "unknown",
            "traversant": true},                             # optional (true)
        "adjacency": "detached" | "one_shared_wall" | "two_shared_walls",
        "wall_insulation":  {"state": "uninsulated" | "period_default"
                                      | "renovated" | "known_r",
                             # known_r only — either an explicit R, or an
                             # insulation material + thickness (R = e/lambda,
                             # lambda from tables/insulation_materials.json):
                             "r_value_m2k_per_w": 3.7,
                             "material": "glass_wool", "thickness_cm": 20},
        "roof_insulation":  {...same...},
        "floor_insulation": {...same...},
        "floor_type": "unknown" | "terre_plein" | "vide_sanitaire"          # optional
                      | "sous_sol_non_chauffe" | "local_non_chauffe",
        "glazing": "single_glazing" | ... | "triple_glazing",
        "glazing_orientation": "unknown" | "south" | "east_west" | "north",  # optional
        "solar_shading": "clear_or_unknown" | "partial" | "heavy",          # optional
        "inertia": "unknown" | "light" | "medium" | "heavy",                # optional
        "geometry": {                                        # optional overrides (M-1)
            "ceiling_height_m": 2.5, "wall_area_m2": 83.0, "window_area_m2": 17.0,
            "roof_area_m2": 100.0, "floor_area_m2": 100.0},
        "summer": {                                          # optional (#16 briques 1-2)
            "solar_protections": "full" | "partial" | "none" | "unknown",
            "fixed_air_circulators": false,
            "air_conditioning": false,
            "air_conditioning_period": "before_2008" | "2008_2014"
                                       | "from_2015" | "unknown"},
        "heating": {"generator": "...", "carrier": "...", "age_years": 30},
        "dhw": {"generator": "...", "carrier": "..."},       # carrier optional
        "ventilation": {"type": "...", "installed_after_2012": false},
        "occupants": 4                                       # optional
      },
      "occupancy": {"mode": "conventional"}
                 | {"mode": "personalized", "heating_setpoint_c": 20,
                    "occupants": 3, "dhw_liters_per_day_per_adult": 56,
                    "energy_prices_eur_per_kwh": {"electricity": 0.25}},
      "scenarios": [{"id": "...", "measures": [{"type": "...", ...}]}],
      "label_targets": {"measures": [{"type": "...", ...}]}   # optional; empty
                       # measures = the six default measures (backlog #8)
    }

Output: baseline results (conventional always; personalized when requested,
with ``label`` forced to ``null`` — the DPE label must come from the
conventional run), per-scenario assessments, per-measure cost ranges for the
current building, the predefined bundles and — when ``label_targets`` was
requested — the cheapest measure combination reaching each DPE class better
than the baseline label (exhaustive search over the 2^n - 1 combinations).
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from typing import Any, cast

from renosim import SCHEMA_VERSION, __version__
from renosim.economics import assess_scenario, measure_cost_range
from renosim.envelope import DEFAULT_CEILING_HEIGHT_M, default_u_values
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
    GlazingOrientation,
    HeatingGeneratorType,
    HeatingSystem,
    InertiaClass,
    OpaqueEnvelopeElement,
    SolarProtectionLevel,
    SolarShading,
    VentilationSystem,
    VentilationType,
    Window,
)
from renosim.occupancy import CONVENTIONAL, OccupancyScenario
from renosim.outputs import (
    DEFAULT_REGULATION_VINTAGE,
    REGULATION_VINTAGES,
    RegulationVintage,
    annual_energy_cost_eur,
)
from renosim.renovation import (
    DEFAULT_ROOF_ADDED_R,
    DEFAULT_WALL_ADDED_R,
    DHWUpgrade,
    HeatingReplacement,
    RenovationMeasure,
    RoofInsulation,
    SolarProtectionInstallation,
    VentilationUpgrade,
    WallInsulation,
    WindowReplacement,
    added_r_from_insulation,
    apply_measures,
    predefined_bundles,
)
from renosim.simulation import SimulationResult, simulate
from renosim.summer_comfort import SummerComfortAssessment, assess_summer_comfort
from renosim.tables_io import load_table

#: Exposed-perimeter fraction per adjacency (square footprint, 4 facades):
#: each shared facade removes a quarter of the perimeter.
_ADJACENCY_EXPOSED_FRACTION = {
    "detached": 1.0,
    "one_shared_wall": 0.75,
    "two_shared_walls": 0.5,
}

#: M-1: window area = Sh / 6 (historical DPE convention for unknown glazing area).
WINDOW_AREA_FRACTION = 1.0 / 6.0

#: Floor for the reconstructed exposed wall area (mirrors validation M-1).
MIN_WALL_AREA_M2 = 10.0

_INSULATION_STATES = ("uninsulated", "period_default", "renovated", "known_r")

#: Default carrier implied by a DHW generator when the form does not send one.
_DHW_DEFAULT_CARRIER = {
    DHWGeneratorType.ELECTRIC_STORAGE: EnergyCarrier.ELECTRICITY,
    DHWGeneratorType.GAS_STORAGE_OR_INSTANT: EnergyCarrier.NATURAL_GAS,
    DHWGeneratorType.HEAT_PUMP_WATER_HEATER: EnergyCarrier.ELECTRICITY,
}

#: JSON measure-type names, in the canonical card order of the app.
_MEASURE_TYPES = (
    "wall_insulation",
    "roof_insulation",
    "window_replacement",
    "ventilation_upgrade",
    "heating_replacement",
    "dhw_upgrade",
    "solar_protection_installation",
)

#: Measures explored by the default label-target search: the summer-only
#: solar-protection measure cannot improve the label (no energy effect) and
#: would only double the 2^n search space.
_LABEL_TARGET_TYPES = tuple(t for t in _MEASURE_TYPES if t != "solar_protection_installation")


#: Apartment positions accepted by the form; "unknown" is treated as an
#: intermediate floor (the most common configuration, deviation D-18).
_APARTMENT_POSITIONS = ("ground", "intermediate", "top", "unknown")

#: Floor adjacency types accepted by the form; "unknown" keeps the M-7
#: calibrated treatment (vide sanitaire / sous-sol Ue table).
_FLOOR_TYPES = (
    "unknown",
    "terre_plein",
    "vide_sanitaire",
    "sous_sol_non_chauffe",
    "local_non_chauffe",
)

#: Construction periods using the "à partir de 2001" terre-plein Ue table.
_POST_2001_PERIODS = frozenset(
    {
        ConstructionPeriod.Y2001_2005,
        ConstructionPeriod.Y2006_2012,
        ConstructionPeriod.AFTER_2013,
    }
)


def _interpolate_ue(upb_w_per_m2k: float, table: Mapping[str, Any]) -> float:
    """Linear interpolation of Ue between the tabulated Upb columns."""
    upb_col = [float(v) for v in table["upb_w_per_m2k"]]
    ue_col = [float(v) for v in table["ue_w_per_m2k"]]
    if upb_w_per_m2k >= upb_col[0]:
        return ue_col[0]
    if upb_w_per_m2k <= upb_col[-1]:
        return ue_col[-1]
    for i in range(len(upb_col) - 1):
        u1, u2 = upb_col[i], upb_col[i + 1]
        if u2 <= upb_w_per_m2k <= u1:
            e1, e2 = ue_col[i], ue_col[i + 1]
            return e2 + (e1 - e2) * (upb_w_per_m2k - u2) / (u1 - u2)
    return ue_col[0]  # pragma: no cover


def _ground_floor_b(
    upb_w_per_m2k: float, floor_type: str = "unknown", period: ConstructionPeriod | None = None
) -> float:
    """b coefficient of the ground floor per its adjacency (3CL §3.1/§3.2.2).

    - ``terre_plein``: official terre-plein Ue tables (p.19, pre/post 2001);
    - ``vide_sanitaire`` / ``sous_sol_non_chauffe`` / ``unknown``: the M-7
      vide-sanitaire/sous-sol Ue table (p.18) — the Phase 3 calibrated default;
    - ``local_non_chauffe``: flat b from the §3.1 b table (garage/cellier).

    Ue-based values are applied as b = Ue/Upb clamped to [0.15, 1] with the
    2S/P = 5 row (M-7 convention).
    """
    if floor_type not in _FLOOR_TYPES:
        raise ValueError(f"unknown floor_type {floor_type!r} (expected one of {_FLOOR_TYPES})")
    tables = load_table("u_values_default")
    if floor_type == "local_non_chauffe":
        return float(tables["floor_b_unheated_space"]["b"])
    if floor_type == "terre_plein":
        vintage = "post_2001" if period in _POST_2001_PERIODS else "pre_2001"
        ue = _interpolate_ue(upb_w_per_m2k, tables["ground_contact_ue_terre_plein"][vintage])
    else:
        ue = _interpolate_ue(upb_w_per_m2k, tables["ground_contact_ue"])
    return min(1.0, max(0.15, ue / upb_w_per_m2k))


def _uninsulated_u(element: str) -> float:
    """Uninsulated default U: traditional-wall mid-range for walls (M-6)."""
    base = load_table("u_values_default")["uninsulated_defaults"]
    key = {
        "wall": "wall_u_nu_traditional",
        "roof": "roof_u0",
        "floor": "floor_u0",
    }[element]
    return float(base[key])


def _resolve_opaque_u(
    spec: Mapping[str, Any],
    element: str,
    period: ConstructionPeriod,
    zone: ClimateZone,
    electric_joule: bool,
) -> float:
    """U-value from the form insulation state, official table values only."""
    state = str(spec.get("state", "period_default"))
    if state not in _INSULATION_STATES:
        raise ValueError(f"unknown insulation state {state!r} for {element}")
    if state == "uninsulated":
        return _uninsulated_u(element)
    if state == "known_r":
        if spec.get("material") is not None:
            added_r = added_r_from_insulation(str(spec["material"]), float(spec["thickness_cm"]))
        else:
            added_r = float(spec["r_value_m2k_per_w"])
            if added_r <= 0:
                raise ValueError(f"r_value_m2k_per_w must be positive, got {added_r}")
        base_u = _uninsulated_u(element)
        return 1.0 / (1.0 / base_u + added_r)
    lookup_period = ConstructionPeriod.AFTER_2013 if state == "renovated" else period
    defaults = default_u_values(lookup_period, zone, insulated=True, electric_joule=electric_joule)
    return {"wall": defaults.wall, "roof": defaults.roof, "floor": defaults.floor}[element]


def building_from_json(data: Mapping[str, Any]) -> Building:
    """Build a :class:`Building` from the form-level description.

    House geometry is reconstructed per choice M-1 (square footprint of
    ``Sh / levels``, walls = exposed perimeter x ceiling height x levels minus
    windows, roof = floor = footprint, windows = Sh/6), with the exposed
    perimeter reduced by 25 % per shared facade.

    Apartment geometry (D-18): single level, square footprint of ``Sh``;
    a through apartment exposes two opposite facades (50 % of the perimeter),
    a non-through one exposes one facade (25 %) plus one facade on the common
    circulation (official b = 0.35); the two remaining sides adjoin heated
    dwellings (b = 0, not modelled). Ceiling and floor follow the declared
    position: intermediate/unknown -> both adjacent to heated dwellings
    (b = 0), top -> exposed roof, ground -> the house ground-floor treatment.
    """
    sh = float(data["living_area_m2"])
    levels = max(1, int(data.get("levels", 1)))
    geometry = cast(Mapping[str, Any], data.get("geometry") or {})

    def _override(key: str) -> float | None:
        raw = geometry.get(key)
        if raw is None:
            return None
        value = float(raw)
        if value <= 0:
            raise ValueError(f"geometry {key} must be positive, got {value}")
        return value

    hsp_override = _override("ceiling_height_m")
    declared_hsp = (
        hsp_override
        if hsp_override is not None
        else (float(data["ceiling_height_m"]) if "ceiling_height_m" in data else None)
    )
    hsp = declared_hsp if declared_hsp is not None else DEFAULT_CEILING_HEIGHT_M
    period = ConstructionPeriod(str(data["construction_period"]))
    zone = ClimateZone(str(data["climate_zone"]))
    altitude = AltitudeClass(str(data["altitude_class"]))

    adjacency = str(data.get("adjacency", "detached"))
    if adjacency not in _ADJACENCY_EXPOSED_FRACTION:
        raise ValueError(f"unknown adjacency {adjacency!r}")

    heating_data = cast(Mapping[str, Any], data["heating"])
    generator = HeatingGeneratorType(str(heating_data["generator"]))
    age_raw = heating_data.get("age_years")
    heating = HeatingSystem(
        generator_type=generator,
        energy_carrier=EnergyCarrier(str(heating_data["carrier"])),
        generator_age_years=float(age_raw) if age_raw is not None else None,
    )
    joule = generator is HeatingGeneratorType.ELECTRIC_JOULE

    dhw_data = cast(Mapping[str, Any], data["dhw"])
    dhw_generator = DHWGeneratorType(str(dhw_data["generator"]))
    if dhw_data.get("carrier") is not None:
        dhw_carrier = EnergyCarrier(str(dhw_data["carrier"]))
    elif dhw_generator is DHWGeneratorType.COUPLED_TO_HEATING_SYSTEM:
        dhw_carrier = heating.energy_carrier
    else:
        dhw_carrier = _DHW_DEFAULT_CARRIER[dhw_generator]

    vent_data = cast(Mapping[str, Any], data["ventilation"])
    ventilation = VentilationSystem(
        ventilation_type=VentilationType(str(vent_data["type"])),
        installed_after_2012=bool(vent_data.get("installed_after_2012", False)),
    )

    dwelling = DwellingType(str(data.get("dwelling_type", "house")))
    apartment_data = cast(Mapping[str, Any], data.get("apartment") or {})
    position = str(apartment_data.get("position", "unknown"))
    if position not in _APARTMENT_POSITIONS:
        raise ValueError(
            f"unknown apartment position {position!r} (expected one of {_APARTMENT_POSITIONS})"
        )
    traversant = bool(apartment_data.get("traversant", True))

    if dwelling is DwellingType.APARTMENT:
        levels = 1
    footprint = sh / levels
    full_perimeter = 4.0 * math.sqrt(footprint)
    if dwelling is DwellingType.APARTMENT:
        # Through flat: 2 opposite exposed facades; else 1 exposed facade.
        perimeter = full_perimeter * (0.5 if traversant else 0.25)
    else:
        perimeter = full_perimeter * _ADJACENCY_EXPOSED_FRACTION[adjacency]
    window_override = _override("window_area_m2")
    window_area = window_override if window_override is not None else sh * WINDOW_AREA_FRACTION
    wall_override = _override("wall_area_m2")
    if wall_override is not None:
        wall_area = wall_override
    else:
        wall_area = max(
            MIN_WALL_AREA_M2 if dwelling is DwellingType.HOUSE else MIN_WALL_AREA_M2 / 2.0,
            perimeter * hsp * levels - window_area,
        )
        if dwelling is DwellingType.APARTMENT:
            # Calibrated deperditive-wall factor (gables, party walls on
            # unheated spaces — see apartment_reconstruction table note).
            wall_area *= float(
                load_table("u_values_default")["apartment_reconstruction"]["wall_area_factor"]
            )
    roof_override = _override("roof_area_m2")
    roof_area = roof_override if roof_override is not None else footprint
    floor_override = _override("floor_area_m2")
    floor_area = floor_override if floor_override is not None else footprint

    wall_u = _resolve_opaque_u(
        cast(Mapping[str, Any], data["wall_insulation"]), "wall", period, zone, joule
    )
    roof_u = _resolve_opaque_u(
        cast(Mapping[str, Any], data["roof_insulation"]), "roof", period, zone, joule
    )
    floor_u = _resolve_opaque_u(
        cast(Mapping[str, Any], data["floor_insulation"]), "floor", period, zone, joule
    )

    glazing = str(data["glazing"])
    window_defaults = load_table("u_values_default")["window_defaults"]
    if glazing not in window_defaults or glazing == "note":
        raise ValueError(f"unknown glazing {glazing!r}")
    win = window_defaults[glazing]

    floor_type = str(data.get("floor_type", "unknown"))
    orientation = GlazingOrientation(str(data.get("glazing_orientation", "unknown")))
    shading = SolarShading(str(data.get("solar_shading", "clear_or_unknown")))
    inertia = InertiaClass(str(data.get("inertia", "unknown")))

    # Summer-comfort inputs (#16 brique 1). The roof-insulation state declared
    # for the winter U-value doubles as the annexe 9 roof criterion:
    # "period_default" means unknown -> official pre/post-1975 default.
    summer = cast(Mapping[str, Any], data.get("summer") or {})
    solar_protections = SolarProtectionLevel(str(summer.get("solar_protections", "unknown")))
    roof_spec = cast(Mapping[str, Any], data["roof_insulation"])
    roof_state = str(roof_spec.get("state", "period_default"))
    roof_insulated = {"uninsulated": False, "renovated": True, "known_r": True}.get(roof_state)

    walls: list[OpaqueEnvelopeElement] = [
        OpaqueEnvelopeElement(area_m2=wall_area, u_value_w_per_m2k=wall_u)
    ]
    if dwelling is DwellingType.APARTMENT:
        # Ceiling/floor adjacency per position; party surfaces to heated
        # dwellings have b = 0 (no loss); an unknown position uses the
        # calibrated expected-value b (apartment_reconstruction table).
        recon = load_table("u_values_default")["apartment_reconstruction"]
        if position == "top":
            roof_b = 1.0
        elif position == "unknown":
            roof_b = float(recon["unknown_position_roof_b"])
        else:
            roof_b = 0.0
        if position == "ground":
            floor_b = _ground_floor_b(floor_u, floor_type, period)
        elif position == "unknown":
            floor_b = float(recon["unknown_position_floor_b"])
        else:
            floor_b = 0.0
        if not traversant:
            # One facade on the unheated common circulation (official b 0.35).
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
        floor_b = _ground_floor_b(floor_u, floor_type, period)

    occupants_raw = data.get("occupants")
    return Building(
        living_area_m2=sh,
        construction_period=period,
        climate_zone=zone,
        altitude_class=altitude,
        walls=tuple(walls),
        roof=OpaqueEnvelopeElement(
            area_m2=roof_area,
            u_value_w_per_m2k=roof_u,
            unheated_space_reduction_coefficient=roof_b,
        ),
        floor=OpaqueEnvelopeElement(
            area_m2=floor_area,
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
        dhw_system=DHWSystem(generator_type=dhw_generator, energy_carrier=dhw_carrier),
        ventilation_system=ventilation,
        number_of_occupants=int(occupants_raw) if occupants_raw is not None else None,
        glazing_orientation=orientation,
        solar_shading=shading,
        inertia=inertia,
        dwelling_type=dwelling,
        single_exposed_facade=dwelling is DwellingType.APARTMENT and not traversant,
        exterior_solar_protections=solar_protections,
        has_fixed_air_circulators=bool(summer.get("fixed_air_circulators", False)),
        has_air_conditioning=bool(summer.get("air_conditioning", False)),
        air_conditioning_period=CoolingPeriod(
            str(summer.get("air_conditioning_period", "unknown"))
        ),
        roof_insulated=roof_insulated,
        through_dwelling=traversant if dwelling is DwellingType.APARTMENT else None,
        ceiling_height_m=declared_hsp,
    )


def _measure_added_r(item: Mapping[str, Any], default_r: float) -> float:
    """Added R of an insulation measure: material + thickness, explicit R, or default."""
    if item.get("material") is not None:
        return added_r_from_insulation(str(item["material"]), float(item["thickness_cm"]))
    return float(item.get("added_r_m2k_per_w", default_r))


def parse_measures(items: Sequence[Mapping[str, Any]]) -> tuple[RenovationMeasure, ...]:
    """Parse JSON measure descriptions into engine measures."""
    measures: list[RenovationMeasure] = []
    for item in items:
        mtype = str(item.get("type"))
        if mtype == "wall_insulation":
            measures.append(
                WallInsulation(added_r_m2k_per_w=_measure_added_r(item, DEFAULT_WALL_ADDED_R))
            )
        elif mtype == "roof_insulation":
            measures.append(
                RoofInsulation(added_r_m2k_per_w=_measure_added_r(item, DEFAULT_ROOF_ADDED_R))
            )
        elif mtype == "window_replacement":
            measures.append(
                WindowReplacement(glazing=str(item.get("glazing", "double_glazing_low_e")))
            )
        elif mtype == "ventilation_upgrade":
            measures.append(
                VentilationUpgrade(
                    new_type=VentilationType(
                        str(item.get("new_type", VentilationType.EXHAUST_ONLY_HYGRO_B.value))
                    )
                )
            )
        elif mtype == "heating_replacement":
            measures.append(
                HeatingReplacement(
                    new_generator=HeatingGeneratorType(
                        str(
                            item.get(
                                "new_generator", HeatingGeneratorType.HEAT_PUMP_AIR_WATER.value
                            )
                        )
                    )
                )
            )
        elif mtype == "dhw_upgrade":
            measures.append(DHWUpgrade())
        elif mtype == "solar_protection_installation":
            measures.append(SolarProtectionInstallation())
        else:
            raise ValueError(f"unknown measure type: {mtype!r}")
    return tuple(measures)


def _measure_to_json(measure: RenovationMeasure) -> dict[str, Any]:
    """Serialise a measure back to its JSON description."""
    if isinstance(measure, WallInsulation):
        return {"type": "wall_insulation", "added_r_m2k_per_w": measure.added_r_m2k_per_w}
    if isinstance(measure, RoofInsulation):
        return {"type": "roof_insulation", "added_r_m2k_per_w": measure.added_r_m2k_per_w}
    if isinstance(measure, WindowReplacement):
        return {"type": "window_replacement", "glazing": measure.glazing}
    if isinstance(measure, VentilationUpgrade):
        return {"type": "ventilation_upgrade", "new_type": measure.new_type.value}
    if isinstance(measure, HeatingReplacement):
        return {"type": "heating_replacement", "new_generator": measure.new_generator.value}
    if isinstance(measure, DHWUpgrade):
        return {"type": "dhw_upgrade"}
    if isinstance(measure, SolarProtectionInstallation):
        return {"type": "solar_protection_installation"}
    raise ValueError(f"unserialisable measure: {measure!r}")  # pragma: no cover


def _default_measure(mtype: str) -> RenovationMeasure:
    return parse_measures(({"type": mtype},))[0]


def _annual_cost(
    by_carrier: Mapping[EnergyCarrier, float], overrides: Mapping[str, float] | None
) -> float:
    """Annual cost, with optional flat user prices per carrier (personalized mode).

    Overridden carriers use ``kWh x price``; the others keep the conventional
    tariffs of ``annual_energy_cost_eur`` (computed per carrier, which matches
    the engine's total since tariffs are independent per carrier).
    """
    if not overrides:
        return annual_energy_cost_eur(dict(by_carrier))
    total = 0.0
    for carrier, kwh in by_carrier.items():
        if kwh <= 0:
            continue
        if carrier.value in overrides:
            total += kwh * float(overrides[carrier.value])
        else:
            total += annual_energy_cost_eur({carrier: kwh})
    return total


def _result_to_json(
    result: SimulationResult, price_overrides: Mapping[str, float] | None = None
) -> dict[str, Any]:
    """Serialise a simulation result; labels are null on non-conventional runs."""
    conventional = result.is_conventional
    env = result.envelope
    return {
        "is_conventional": conventional,
        "label": result.label if conventional else None,
        "energy_class": result.energy_class if conventional else None,
        "climate_class": result.climate_class if conventional else None,
        "primary_energy_kwh_m2": result.primary_energy_kwh_m2,
        "final_energy_kwh_m2": result.final_energy_kwh_m2,
        "co2_kg_m2": result.co2_kg_m2,
        "annual_cost_eur": (
            result.annual_cost_eur
            if price_overrides is None
            else _annual_cost(result.final_energy_kwh_by_carrier, price_overrides)
        ),
        "final_energy_kwh_by_use": dict(result.final_energy_kwh_by_use),
        "final_energy_kwh_by_carrier": {
            carrier.value: kwh for carrier, kwh in result.final_energy_kwh_by_carrier.items()
        },
        "needs": {
            "heating_kwh": result.needs.heating_kwh,
            "dhw_kwh": result.needs.dhw_kwh,
            "cooling_kwh": result.needs.cooling_kwh,
        },
        "envelope": {
            "walls_w_per_k": env.walls_w_per_k,
            "roof_w_per_k": env.roof_w_per_k,
            "floor_w_per_k": env.floor_w_per_k,
            "windows_w_per_k": env.windows_w_per_k,
            "thermal_bridges_w_per_k": env.thermal_bridges_w_per_k,
            "ventilation_w_per_k": env.ventilation_w_per_k,
            "infiltration_w_per_k": env.infiltration_w_per_k,
            "total_w_per_k": env.gv_w_per_k,
        },
    }


def _summer_comfort_to_json(assessment: SummerComfortAssessment) -> dict[str, Any]:
    """Serialise a passive summer-comfort assessment (#16 brique 1)."""
    return {
        "level": assessment.level.value,
        "criteria": {
            "roof_criterion_applicable": assessment.roof_criterion_applicable,
            "roof_insulated": assessment.roof_insulated,
            "solar_protections_full": assessment.solar_protections_full,
            "heavy_inertia": assessment.heavy_inertia,
            "through_dwelling": assessment.through_dwelling,
            "fixed_air_circulators": assessment.fixed_air_circulators,
        },
    }


def _assessment_to_json(
    before: SimulationResult,
    after: SimulationResult,
    investment_low_eur: float,
    investment_high_eur: float,
    living_area_m2: float,
    price_overrides: Mapping[str, float] | None,
) -> dict[str, Any]:
    cost_before = (
        before.annual_cost_eur
        if price_overrides is None
        else _annual_cost(before.final_energy_kwh_by_carrier, price_overrides)
    )
    cost_after = (
        after.annual_cost_eur
        if price_overrides is None
        else _annual_cost(after.final_energy_kwh_by_carrier, price_overrides)
    )
    savings_eur = cost_before - cost_after
    payback_low = investment_low_eur / savings_eur if savings_eur > 0 else None
    payback_high = investment_high_eur / savings_eur if savings_eur > 0 else None
    return {
        "investment_low_eur": investment_low_eur,
        "investment_high_eur": investment_high_eur,
        "annual_savings_eur": savings_eur,
        "annual_energy_savings_kwh": (
            (before.final_energy_kwh_m2 - after.final_energy_kwh_m2) * living_area_m2
        ),
        "annual_co2_savings_kg": (before.co2_kg_m2 - after.co2_kg_m2) * living_area_m2,
        "payback_years_low": payback_low,
        "payback_years_high": payback_high,
        "after": _result_to_json(after, price_overrides),
    }


#: DPE classes from best to worst, for the label-target search ranking.
_DPE_CLASSES = ("A", "B", "C", "D", "E", "F", "G")


def _label_targets(
    building: Building,
    baseline: SimulationResult,
    measures: Sequence[RenovationMeasure],
    vintage: RegulationVintage,
) -> dict[str, Any]:
    """Cheapest measure combination reaching each class better than the baseline.

    Exhaustive search over the non-empty subsets of ``measures`` (63 with the
    six V1 measures — well under a second, backlog #8). A subset counts for a
    target class when its post-renovation conventional label is at least as
    good; ties are broken by the lowest mid-range investment.
    """
    costs = [measure_cost_range(building, m) for m in measures]
    baseline_rank = _DPE_CLASSES.index(str(baseline.label))
    best: dict[int, tuple[float, dict[str, Any]]] = {}
    n = len(measures)
    for mask in range(1, 1 << n):
        picked = [i for i in range(n) if mask >> i & 1]
        subset = tuple(measures[i] for i in picked)
        after = simulate(apply_measures(building, subset), CONVENTIONAL, vintage)
        rank = _DPE_CLASSES.index(str(after.label))
        if rank >= baseline_rank:
            continue
        low = sum(costs[i][0] for i in picked)
        high = sum(costs[i][1] for i in picked)
        mid = (low + high) / 2.0
        savings = baseline.annual_cost_eur - after.annual_cost_eur
        entry = {
            "measures": [_measure_to_json(m) for m in subset],
            "investment_low_eur": low,
            "investment_high_eur": high,
            "annual_savings_eur": savings,
            "annual_co2_savings_kg": (
                (baseline.co2_kg_m2 - after.co2_kg_m2) * building.living_area_m2
            ),
            "payback_years_low": low / savings if savings > 0 else None,
            "payback_years_high": high / savings if savings > 0 else None,
            "after_label": after.label,
            "after_primary_energy_kwh_m2": after.primary_energy_kwh_m2,
        }
        # The subset satisfies every target from its own class down to one
        # class above the baseline.
        for target in range(rank, baseline_rank):
            current = best.get(target)
            if current is None or mid < current[0]:
                best[target] = (mid, entry)
    return {_DPE_CLASSES[rank]: entry for rank, (_, entry) in best.items()}


def _parse_occupancy(
    occ: Mapping[str, Any],
) -> tuple[OccupancyScenario | None, dict[str, float] | None]:
    """Personalized scenario and price overrides, or (None, None) in conventional mode."""
    mode = str(occ.get("mode", "conventional"))
    if mode == "conventional":
        return None, None
    if mode != "personalized":
        raise ValueError(f"unknown occupancy mode {mode!r}")
    occupants_raw = occ.get("occupants")
    scenario = OccupancyScenario(
        heating_setpoint_c=float(occ.get("heating_setpoint_c", 19.0)),
        dhw_liters_per_day_per_adult=float(occ.get("dhw_liters_per_day_per_adult", 56.0)),
        occupants_override=float(occupants_raw) if occupants_raw is not None else None,
    )
    overrides_raw = occ.get("energy_prices_eur_per_kwh")
    overrides = (
        {str(k): float(v) for k, v in cast(Mapping[str, Any], overrides_raw).items()}
        if overrides_raw
        else None
    )
    return scenario, overrides


def _conventions_to_json(vintage: RegulationVintage) -> dict[str, Any]:
    """Conventions applied to this run, for display (vintage, PE factor, prices)."""
    factors = load_table("emission_factors")["primary_energy_factor"][vintage]
    prices = load_table("energy_prices")["_meta"]
    return {
        "regulation_vintage": vintage,
        "electricity_primary_energy_factor": float(factors["electricity"]),
        "energy_prices": {
            "label": str(prices["source_label_fr"]),
            "date_reference": str(prices["date_reference"]),
            "date_in_force": str(prices["date_in_force"]),
        },
    }


def run_simulation(payload_json: str) -> str:
    """Single entry point called from JavaScript: JSON in, JSON out.

    Parameters
    ----------
    payload_json
        Input payload serialised to JSON (schema documented in the module
        docstring).

    Returns
    -------
    str
        Output payload serialised to JSON: baseline (conventional +
        personalized), scenario assessments, per-measure cost ranges and the
        predefined bundles.
    """
    payload = cast(Mapping[str, Any], json.loads(payload_json))
    version = str(payload.get("schema_version"))
    if version != SCHEMA_VERSION:
        raise ValueError(
            f"unsupported schema_version {version!r}; this engine speaks {SCHEMA_VERSION!r}"
        )
    vintage_raw = str(payload.get("regulation_vintage", DEFAULT_REGULATION_VINTAGE))
    if vintage_raw not in REGULATION_VINTAGES:
        raise ValueError(f"unknown regulation_vintage {vintage_raw!r}")
    vintage: RegulationVintage = vintage_raw

    building = building_from_json(cast(Mapping[str, Any], payload["building"]))
    personalized, price_overrides = _parse_occupancy(
        cast(Mapping[str, Any], payload.get("occupancy") or {})
    )

    baseline_conventional = simulate(building, CONVENTIONAL, vintage)
    baseline_personalized = (
        simulate(building, personalized, vintage) if personalized is not None else None
    )

    scenarios_out: list[dict[str, Any]] = []
    for scenario_data in cast(Sequence[Mapping[str, Any]], payload.get("scenarios", ())):
        measures = parse_measures(
            cast(Sequence[Mapping[str, Any]], scenario_data.get("measures", ()))
        )
        assessment = assess_scenario(building, measures, CONVENTIONAL, vintage)
        entry: dict[str, Any] = {
            "id": str(scenario_data.get("id", "")),
            "measures": [_measure_to_json(m) for m in measures],
            "conventional": _assessment_to_json(
                assessment.before,
                assessment.after,
                assessment.investment_low_eur,
                assessment.investment_high_eur,
                building.living_area_m2,
                None,
            ),
            "personalized": None,
            # The passive indicator can improve too (roof insulation, #16).
            "summer_comfort_after": _summer_comfort_to_json(
                assess_summer_comfort(assessment.building_after)
            ),
        }
        if personalized is not None:
            after_perso = simulate(assessment.building_after, personalized, vintage)
            before_perso = cast(SimulationResult, baseline_personalized)
            entry["personalized"] = _assessment_to_json(
                before_perso,
                after_perso,
                assessment.investment_low_eur,
                assessment.investment_high_eur,
                building.living_area_m2,
                price_overrides,
            )
        scenarios_out.append(entry)

    # Per-measure cost ranges and a standalone conventional preview (savings,
    # payback, CO2, resulting label) for each of the six measures on the current
    # building — lets the app rank the cards ("most profitable", "biggest CO2
    # gain") before any measure is activated.
    measure_costs = {}
    measure_previews = {}
    for mtype in _MEASURE_TYPES:
        measure = _default_measure(mtype)
        low, high = measure_cost_range(building, measure)
        measure_costs[mtype] = {"low_eur": low, "high_eur": high}
        preview = assess_scenario(building, (measure,), CONVENTIONAL, vintage)
        measure_previews[mtype] = {
            "annual_savings_eur": preview.annual_savings_eur,
            "annual_energy_savings_kwh": preview.annual_energy_savings_kwh,
            "annual_co2_savings_kg": preview.annual_co2_savings_kg,
            "payback_years_low": (
                preview.payback_years_low if math.isfinite(preview.payback_years_low) else None
            ),
            "payback_years_high": (
                preview.payback_years_high if math.isfinite(preview.payback_years_high) else None
            ),
            "after_label": preview.after.label,
            "summer_comfort_level_after": assess_summer_comfort(preview.building_after).level.value,
        }

    # Label-target search (backlog #8), opt-in: 2^n - 1 extra simulations.
    label_targets: dict[str, Any] | None = None
    targets_req = payload.get("label_targets")
    if targets_req is not None:
        target_items = cast(
            Sequence[Mapping[str, Any]], cast(Mapping[str, Any], targets_req).get("measures") or ()
        )
        target_measures = (
            parse_measures(target_items)
            if target_items
            else tuple(_default_measure(t) for t in _LABEL_TARGET_TYPES)
        )
        label_targets = _label_targets(building, baseline_conventional, target_measures, vintage)

    output = {
        "schema_version": SCHEMA_VERSION,
        "engine": {"name": "renosim", "version": __version__},
        "conventions": _conventions_to_json(vintage),
        "baseline": {
            "conventional": _result_to_json(baseline_conventional),
            "personalized": (
                _result_to_json(baseline_personalized, price_overrides)
                if baseline_personalized is not None
                else None
            ),
        },
        "summer_comfort": {
            **_summer_comfort_to_json(assess_summer_comfort(building)),
            "air_conditioning": building.has_air_conditioning,
            # Conventional cooling need (28 degC): the "what summer would cost
            # if you cooled it" physical indicator (#16 brique 2).
            "cooling_need_kwh": baseline_conventional.needs.cooling_kwh,
            "cooling_need_kwh_m2": (
                baseline_conventional.needs.cooling_kwh / building.living_area_m2
            ),
        },
        "scenarios": scenarios_out,
        "measure_costs": measure_costs,
        "measure_previews": measure_previews,
        "bundles": {
            name: [_measure_to_json(m) for m in measures]
            for name, measures in predefined_bundles().items()
        },
        "label_targets": label_targets,
    }
    return json.dumps(output)


__all__ = [
    "building_from_json",
    "parse_measures",
    "run_simulation",
]
