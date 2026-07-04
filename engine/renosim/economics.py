"""Economics of renovation scenarios: costs, annual savings, simple payback.

Costs are ALWAYS ranges (low/high, sourced in tables/renovation_costs.json).
Savings compare energy costs before/after at the heating + DHW + auxiliaries +
lighting scope. Payback is the simple ratio investment / annual savings
(no discounting in V1 — VAN/TRI is out of scope, CLAUDE.md §2.2).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from renosim.models import Building
from renosim.occupancy import CONVENTIONAL, OccupancyScenario
from renosim.outputs import RegulationVintage
from renosim.renovation import RenovationMeasure, apply_measures
from renosim.simulation import SimulationResult, simulate
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


def measure_cost_range(building: Building, measure: RenovationMeasure) -> tuple[float, float]:
    """Investment cost range (low, high) in EUR for one measure on this building.

    Unit costs come from tables/renovation_costs.json: per m2 of the relevant
    surface for envelope measures, lump sums for systems.
    """
    entry = load_table("renovation_costs")["measures"][measure.cost_key]
    unit = str(entry["unit"])
    low, high = float(entry["low"]), float(entry["high"])
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


def assess_scenario(
    building: Building,
    measures: Sequence[RenovationMeasure],
    scenario: OccupancyScenario = CONVENTIONAL,
    regulation_vintage: RegulationVintage = "dpe_2021",
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
