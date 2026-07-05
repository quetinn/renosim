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
      "regulation_vintage": "dpe_2021" | "dpe_2026",        # optional
      "building": {
        "living_area_m2": 100.0,
        "levels": 1,                                         # optional
        "construction_period": "1948_1974",
        "climate_zone": "H1a",
        "altitude_class": "low",
        "adjacency": "detached" | "one_shared_wall" | "two_shared_walls",
        "wall_insulation":  {"state": "uninsulated" | "period_default"
                                      | "renovated" | "known_r",
                             "r_value_m2k_per_w": 3.7},      # known_r only
        "roof_insulation":  {...same...},
        "floor_insulation": {...same...},
        "glazing": "single_glazing" | ... | "triple_glazing",
        "heating": {"generator": "...", "carrier": "...", "age_years": 30},
        "dhw": {"generator": "...", "carrier": "..."},       # carrier optional
        "ventilation": {"type": "...", "installed_after_2012": false},
        "occupants": 4                                       # optional
      },
      "occupancy": {"mode": "conventional"}
                 | {"mode": "personalized", "heating_setpoint_c": 20,
                    "occupants": 3, "dhw_liters_per_day_per_adult": 56,
                    "energy_prices_eur_per_kwh": {"electricity": 0.25}},
      "scenarios": [{"id": "...", "measures": [{"type": "...", ...}]}]
    }

Output: baseline results (conventional always; personalized when requested,
with ``label`` forced to ``null`` — the DPE label must come from the
conventional run), per-scenario assessments, per-measure cost ranges for the
current building, and the predefined bundles.
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
from renosim.occupancy import CONVENTIONAL, OccupancyScenario
from renosim.outputs import RegulationVintage, annual_energy_cost_eur
from renosim.renovation import (
    DEFAULT_ROOF_ADDED_R,
    DEFAULT_WALL_ADDED_R,
    DHWUpgrade,
    HeatingReplacement,
    RenovationMeasure,
    RoofInsulation,
    VentilationUpgrade,
    WallInsulation,
    WindowReplacement,
    predefined_bundles,
)
from renosim.simulation import SimulationResult, simulate
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
)


def _ground_floor_b(upb_w_per_m2k: float) -> float:
    """Choice M-7: b = Ue/Upb from the official ground-contact table (2S/P = 5)."""
    table = load_table("u_values_default")["ground_contact_ue"]
    upb_col = [float(v) for v in table["upb_w_per_m2k"]]
    ue_col = [float(v) for v in table["ue_w_per_m2k"]]
    if upb_w_per_m2k >= upb_col[0]:
        ue = ue_col[0]
    elif upb_w_per_m2k <= upb_col[-1]:
        ue = ue_col[-1]
    else:
        ue = ue_col[0]
        for i in range(len(upb_col) - 1):
            u1, u2 = upb_col[i], upb_col[i + 1]
            if u2 <= upb_w_per_m2k <= u1:
                e1, e2 = ue_col[i], ue_col[i + 1]
                ue = e2 + (e1 - e2) * (upb_w_per_m2k - u2) / (u1 - u2)
                break
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

    Geometry is reconstructed per choice M-1 (square footprint of
    ``Sh / levels``, walls = exposed perimeter x ceiling height x levels minus
    windows, roof = floor = footprint, windows = Sh/6), with the exposed
    perimeter reduced by 25 % per shared facade.
    """
    sh = float(data["living_area_m2"])
    levels = max(1, int(data.get("levels", 1)))
    hsp = float(data.get("ceiling_height_m", DEFAULT_CEILING_HEIGHT_M))
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

    footprint = sh / levels
    perimeter = 4.0 * math.sqrt(footprint) * _ADJACENCY_EXPOSED_FRACTION[adjacency]
    window_area = sh * WINDOW_AREA_FRACTION
    wall_area = max(MIN_WALL_AREA_M2, perimeter * hsp * levels - window_area)

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

    occupants_raw = data.get("occupants")
    return Building(
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
        dhw_system=DHWSystem(generator_type=dhw_generator, energy_carrier=dhw_carrier),
        ventilation_system=ventilation,
        number_of_occupants=int(occupants_raw) if occupants_raw is not None else None,
    )


def parse_measures(items: Sequence[Mapping[str, Any]]) -> tuple[RenovationMeasure, ...]:
    """Parse JSON measure descriptions into engine measures."""
    measures: list[RenovationMeasure] = []
    for item in items:
        mtype = str(item.get("type"))
        if mtype == "wall_insulation":
            measures.append(
                WallInsulation(
                    added_r_m2k_per_w=float(item.get("added_r_m2k_per_w", DEFAULT_WALL_ADDED_R))
                )
            )
        elif mtype == "roof_insulation":
            measures.append(
                RoofInsulation(
                    added_r_m2k_per_w=float(item.get("added_r_m2k_per_w", DEFAULT_ROOF_ADDED_R))
                )
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
        "needs": {"heating_kwh": result.needs.heating_kwh, "dhw_kwh": result.needs.dhw_kwh},
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
    vintage_raw = str(payload.get("regulation_vintage", "dpe_2021"))
    if vintage_raw not in ("dpe_2021", "dpe_2026"):
        raise ValueError(f"unknown regulation_vintage {vintage_raw!r}")
    vintage = cast(RegulationVintage, vintage_raw)

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

    measure_costs = {}
    for mtype in _MEASURE_TYPES:
        low, high = measure_cost_range(building, _default_measure(mtype))
        measure_costs[mtype] = {"low_eur": low, "high_eur": high}

    output = {
        "schema_version": SCHEMA_VERSION,
        "engine": {"name": "renosim", "version": __version__},
        "baseline": {
            "conventional": _result_to_json(baseline_conventional),
            "personalized": (
                _result_to_json(baseline_personalized, price_overrides)
                if baseline_personalized is not None
                else None
            ),
        },
        "scenarios": scenarios_out,
        "measure_costs": measure_costs,
        "bundles": {
            name: [_measure_to_json(m) for m in measures]
            for name, measures in predefined_bundles().items()
        },
    }
    return json.dumps(output)


__all__ = [
    "building_from_json",
    "parse_measures",
    "run_simulation",
]
