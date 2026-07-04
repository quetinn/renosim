"""End-to-end simulation: Building + OccupancyScenario -> annual results.

Scope of uses (V1): heating + DHW + ventilation auxiliaries + lighting.
Cooling is out of scope (deviation D-02). The DPE label must always be read
from a run with the conventional scenario (occupancy.CONVENTIONAL).
"""

from __future__ import annotations

from dataclasses import dataclass

from renosim.envelope import EnvelopeLosses, envelope_heat_loss
from renosim.models import Building, EnergyCarrier
from renosim.needs import AnnualNeeds, annual_needs
from renosim.occupancy import CONVENTIONAL, OccupancyScenario
from renosim.outputs import (
    RegulationVintage,
    annual_energy_cost_eur,
    co2_emissions_kg,
    dpe_label,
    primary_energy_kwh,
)
from renosim.systems import (
    dhw_consumption,
    heating_consumption,
    lighting_kwh,
    ventilation_auxiliary_kwh,
)


@dataclass(frozen=True, slots=True)
class SimulationResult:
    """Annual simulation results for one building and occupancy scenario.

    Areas are normalized by the living area. ``label`` is only meaningful when
    the run used the conventional scenario (``is_conventional`` is True).
    """

    is_conventional: bool
    envelope: EnvelopeLosses
    needs: AnnualNeeds
    final_energy_kwh_by_use: dict[str, float]
    final_energy_kwh_by_carrier: dict[EnergyCarrier, float]
    final_energy_kwh_m2: float
    primary_energy_kwh_m2: float
    co2_kg_m2: float
    annual_cost_eur: float
    label: str
    energy_class: str
    climate_class: str


def simulate(
    building: Building,
    scenario: OccupancyScenario = CONVENTIONAL,
    regulation_vintage: RegulationVintage = "dpe_2021",
) -> SimulationResult:
    """Run the full calculation chain for a building.

    Parameters
    ----------
    building
        Building description with resolved U-values.
    scenario
        Occupancy scenario; defaults to the conventional DPE scenario.
    regulation_vintage
        DPE primary-energy convention: ``"dpe_2021"`` (electricity 2.3, matches
        the 2021-2025 ADEME validation dataset — V1 default) or ``"dpe_2026"``
        (1.9, in force since 2026-01-01).

    Returns
    -------
    SimulationResult
        Annual energy, emissions, cost and label results.
    """
    envelope = envelope_heat_loss(building)
    needs = annual_needs(building, scenario)

    heating = heating_consumption(building, needs.heating_kwh)
    dhw = dhw_consumption(building, needs.dhw_kwh)
    aux_kwh = ventilation_auxiliary_kwh(building)
    light_kwh = lighting_kwh(building)

    by_use = {
        "heating": heating.final_energy_kwh,
        "dhw": dhw.final_energy_kwh,
        "auxiliaries": aux_kwh,
        "lighting": light_kwh,
    }
    by_carrier: dict[EnergyCarrier, float] = {}
    for carrier, kwh in (
        (heating.energy_carrier, heating.final_energy_kwh),
        (dhw.energy_carrier, dhw.final_energy_kwh),
        (EnergyCarrier.ELECTRICITY, aux_kwh),
        (EnergyCarrier.ELECTRICITY, light_kwh),
    ):
        by_carrier[carrier] = by_carrier.get(carrier, 0.0) + kwh

    sh = building.living_area_m2
    ep_total = (
        primary_energy_kwh(heating.final_energy_kwh, heating.energy_carrier, regulation_vintage)
        + primary_energy_kwh(dhw.final_energy_kwh, dhw.energy_carrier, regulation_vintage)
        + primary_energy_kwh(aux_kwh, EnergyCarrier.ELECTRICITY, regulation_vintage)
        + primary_energy_kwh(light_kwh, EnergyCarrier.ELECTRICITY, regulation_vintage)
    )
    co2_total = (
        co2_emissions_kg(heating.final_energy_kwh, heating.energy_carrier, "heating")
        + co2_emissions_kg(dhw.final_energy_kwh, dhw.energy_carrier, "dhw")
        + co2_emissions_kg(aux_kwh, EnergyCarrier.ELECTRICITY, "auxiliaries")
        + co2_emissions_kg(light_kwh, EnergyCarrier.ELECTRICITY, "lighting")
    )

    cep_m2 = ep_total / sh
    eges_m2 = co2_total / sh
    label = dpe_label(cep_m2, eges_m2, building.climate_zone, building.altitude_class)

    # Individual axis classes for display (energy vs climate sub-labels)
    energy_class = dpe_label(cep_m2, 0.0, building.climate_zone, building.altitude_class)
    climate_class = dpe_label(0.0, eges_m2, building.climate_zone, building.altitude_class)

    return SimulationResult(
        is_conventional=scenario.is_conventional,
        envelope=envelope,
        needs=needs,
        final_energy_kwh_by_use=by_use,
        final_energy_kwh_by_carrier=by_carrier,
        final_energy_kwh_m2=sum(by_use.values()) / sh,
        primary_energy_kwh_m2=cep_m2,
        co2_kg_m2=eges_m2,
        annual_cost_eur=annual_energy_cost_eur(by_carrier),
        label=label,
        energy_class=energy_class,
        climate_class=climate_class,
    )
