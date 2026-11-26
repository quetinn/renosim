"""Economics of renovation scenarios: costs, annual savings, simple payback.

Costs are ALWAYS ranges (low/high, sourced in tables/renovation_costs.json).
Savings compare energy costs before/after at the heating + DHW + auxiliaries +
lighting scope. Payback is the simple ratio investment / annual savings
(no discounting in V1 — VAN/TRI is out of scope, CLAUDE.md §2.2).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from renosim.models import Building, HeatingGeneratorType
from renosim.occupancy import CONVENTIONAL, OccupancyScenario
from renosim.outputs import DEFAULT_REGULATION_VINTAGE, RegulationVintage
from renosim.renovation import RenovationMeasure, apply_measures
from renosim.simulation import SimulationResult, simulate
from renosim.systems import design_heat_load_kw
from renosim.tables_io import load_table


@dataclass(frozen=True, slots=True)
class ScenarioAssessment:
    """Before/after comparison of a renovation scenario.

    ``payback_years_low`` uses the low investment bound (best case) and
    ``payback_years_high`` the high bound; both are ``inf`` when annual savings
    are not positive. The app displays "> 30 ans" beyond that threshold.
    """

    before: SimulationResult
    after: SimulationResult
    building_after: Building
    investment_low_eur: float
    investment_high_eur: float
    annual_savings_eur: float
    annual_energy_savings_kwh: float
    annual_co2_savings_kg: float
    payback_years_low: float
    payback_years_high: float


def cost_index_factor(confidence: str) -> float:
    """BT01 indexation factor from a cost source's price year to the reference date.

    ``reference_value / base_value`` from ``_meta.indexation`` of
    tables/renovation_costs.json (INSEE BT01, base 2010; audit §3.3).
    """
    indexation = load_table("renovation_costs")["_meta"]["indexation"]
    base = float(indexation["base_by_confidence"][confidence]["value"])
    return float(indexation["reference"]["value"]) / base


def measure_cost_range(building: Building, measure: RenovationMeasure) -> tuple[float, float]:
    """Investment cost range (low, high) in EUR for one measure on this building.

    Unit costs come from tables/renovation_costs.json: per m2 of the relevant
    surface for envelope measures, lump sums for systems; each range is
    indexed from its source price year to the reference date (BT01).
    """
    table = load_table("renovation_costs")
    entry = table["measures"][measure.cost_key]
    unit = str(entry["unit"])
    factor = cost_index_factor(str(entry["confidence"]))
    low, high = float(entry["low"]) * factor, float(entry["high"]) * factor
    if unit == "eur_per_m2_wall":
        area = sum(w.area_m2 for w in building.walls)
    elif unit == "eur_per_m2_roof":
        area = building.roof.area_m2
    elif unit == "eur_per_m2_window":
        area = sum(w.area_m2 for w in building.windows)
    elif unit == "eur_lump_sum":
        return low, high
    else:  # pragma: no cover - table integrity
        raise ValueError(f"unknown cost unit: {unit}")
    return low * area, high * area


@dataclass(frozen=True, slots=True)
class HeatPumpSizing:
    """Design heat load of a dwelling getting a new air-to-water heat pump (audit §4.4).

    Attributes
    ----------
    design_heat_load_kw
        Heating power needed at the base temperature after the scenario's
        envelope measures, Pnc (kW, 3CL §15.2.2).
    reference_power_low_kw, reference_power_high_kw
        Power range (kW) the displayed heat-pump cost refers to
        (tables/renovation_costs.json, ADEME guide, 10-12 kW).
    """

    design_heat_load_kw: float
    reference_power_low_kw: float
    reference_power_high_kw: float

    @property
    def above_reference(self) -> bool:
        """True when the needed power exceeds the cost reference range."""
        return self.design_heat_load_kw > self.reference_power_high_kw


def heat_pump_sizing(building_before: Building, building_after: Building) -> HeatPumpSizing | None:
    """Sizing check for a scenario that installs an air-to-water heat pump.

    Returns ``None`` when the scenario keeps the existing generator or installs
    something else. The design load is computed on ``building_after``, i.e.
    after the envelope measures of the same bundle (envelope first, CLAUDE.md
    §4.3). Informational only: consumptions and costs are unchanged.
    """
    new_generator = building_after.heating_system.generator_type
    if (
        new_generator is not HeatingGeneratorType.HEAT_PUMP_AIR_WATER
        or building_before.heating_system.generator_type is new_generator
    ):
        return None
    reference = load_table("renovation_costs")["measures"]["heat_pump_air_water"][
        "reference_power_kw"
    ]
    return HeatPumpSizing(
        design_heat_load_kw=design_heat_load_kw(building_after),
        reference_power_low_kw=float(reference["low"]),
        reference_power_high_kw=float(reference["high"]),
    )


def assess_scenario(
    building: Building,
    measures: Sequence[RenovationMeasure],
    scenario: OccupancyScenario = CONVENTIONAL,
    regulation_vintage: RegulationVintage = DEFAULT_REGULATION_VINTAGE,
) -> ScenarioAssessment:
    """Simulate a renovation scenario and derive its economics.

    Parameters
    ----------
    building
        Current building.
    measures
        Renovation measures (applied in canonical envelope-first order).
    scenario
        Occupancy scenario used for the energy/cost comparison. The labels in
        ``before``/``after`` are only DPE labels when this is conventional.
    regulation_vintage
        DPE primary-energy convention (see outputs.py).

    Returns
    -------
    ScenarioAssessment
        Before/after results, cost range, savings and simple payback bounds.
    """
    before = simulate(building, scenario, regulation_vintage)
    building_after = apply_measures(building, measures)
    after = simulate(building_after, scenario, regulation_vintage)

    inv_low = sum(measure_cost_range(building, m)[0] for m in measures)
    inv_high = sum(measure_cost_range(building, m)[1] for m in measures)

    savings_eur = before.annual_cost_eur - after.annual_cost_eur
    savings_kwh = (before.final_energy_kwh_m2 - after.final_energy_kwh_m2) * (
        building.living_area_m2
    )
    savings_co2 = (before.co2_kg_m2 - after.co2_kg_m2) * building.living_area_m2

    if savings_eur > 0:
        payback_low = inv_low / savings_eur
        payback_high = inv_high / savings_eur
    else:
        payback_low = payback_high = float("inf")

    return ScenarioAssessment(
        before=before,
        after=after,
        building_after=building_after,
        investment_low_eur=inv_low,
        investment_high_eur=inv_high,
        annual_savings_eur=savings_eur,
        annual_energy_savings_kwh=savings_kwh,
        annual_co2_savings_kg=savings_co2,
        payback_years_low=payback_low,
        payback_years_high=payback_high,
    )
