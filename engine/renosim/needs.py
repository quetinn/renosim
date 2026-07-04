"""Heating and DHW needs, monthly, per the simplified 3CL-DPE 2021 chain.

Heating (3CL §6/§9): ``Bch_j = GV * (1 - F_j) * DH_j / 1000`` [kWh] with the
free-gains utilization factor ``F_j`` from the gains/losses ratio and inertia.
Recovered generation/storage losses are ignored (deviation D-07).

DHW (3CL §11.1): ``Becs_j = 1.163 * Nadeq * V * (40 - Tefs_j) * nj_j / 1000``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from renosim.envelope import envelope_heat_loss
from renosim.models import AltitudeClass, Building
from renosim.occupancy import OccupancyScenario, degree_hours_factor, equivalent_adults
from renosim.tables_io import load_table

#: V1 fixed orientation+shading coefficient applied to window solar apertures
#: when building the equivalent south surface (deviation D-06: the simplified
#: journey does not collect per-facade orientations and masks). Calibration
#: candidate for Phase 3.
SOLAR_ORIENTATION_SHADING_COEFFICIENT = 0.5

_ALTITUDE_KEY = {
    AltitudeClass.LOW: "low",
    AltitudeClass.MEDIUM: "medium",
    AltitudeClass.HIGH: "high",
}

_MONTHS = tuple(range(1, 13))


@dataclass(frozen=True, slots=True)
class AnnualNeeds:
    """Annual useful energy needs (kWh), before system efficiencies."""

    heating_kwh: float
    dhw_kwh: float


def _climate(building: Building) -> dict[str, dict[str, dict[str, float]]]:
    table = load_table("climate_zones")
    return cast(
        dict[str, dict[str, dict[str, float]]], table[_ALTITUDE_KEY[building.altitude_class]]
    )


def _monthly(
    climate: dict[str, dict[str, dict[str, float]]], series: str, zone: str, month: int
) -> float:
    return float(climate[series][zone][str(month)])


def monthly_dhw_needs(building: Building, scenario: OccupancyScenario) -> dict[int, float]:
    """Monthly DHW needs Becs_j in kWh (3CL §11.1).

    Parameters
    ----------
    building
        Building description (living area -> equivalent adults, zone -> cold
        water temperature).
    scenario
        Occupancy scenario (draw-off volume, occupant override).

    Returns
    -------
    dict[int, float]
        Needs in kWh keyed by month 1-12.
    """
    occupancy = load_table("occupancy_conventional")
    days: dict[str, float] = occupancy["dhw"]["occupied_days_per_month"]
    heat_capacity = float(occupancy["dhw"]["water_heat_capacity_wh_per_l_k"])
    target_c = float(occupancy["dhw"]["target_temperature_c"])

    climate = _climate(building)
    zone = building.climate_zone.value
    nadeq = equivalent_adults(building.living_area_m2, scenario)
    volume = scenario.dhw_liters_per_day_per_adult

    needs: dict[int, float] = {}
    for month in _MONTHS:
        tefs = _monthly(climate, "tefs_c", zone, month)
        nj = float(days[str(month)])
        needs[month] = heat_capacity * nadeq * volume * (target_c - tefs) * nj / 1000.0
    return needs


def monthly_heating_needs(building: Building, scenario: OccupancyScenario) -> dict[int, float]:
    """Monthly heating needs Bch_j in kWh (3CL §6/§9, simplified).

    Free gains: internal gains (equipment + lighting + occupants, §6.1) plus
    solar gains through windows with a fixed orientation/shading coefficient
    (deviation D-06). Utilization factor F from the X ratio and inertia
    exponents (medium inertia by default in V1).

    Returns
    -------
    dict[int, float]
        Needs in kWh keyed by month 1-12 (0 outside the heating season).
    """
    occupancy = load_table("occupancy_conventional")
    gains_cfg = occupancy["internal_gains"]
    p_equipment = float(gains_cfg["equipment_plus_lighting_w_per_m2"])
    p_adult = float(gains_cfg["per_adult_w"])
    occ_fraction = float(gains_cfg["occupancy_fraction"])
    inertia_exp = float(occupancy["utilization_factor_inertia_exponents"]["medium"])

    climate = _climate(building)
    zone = building.climate_zone.value
    gv = envelope_heat_loss(building).gv_w_per_k
    nadeq = equivalent_adults(building.living_area_m2, scenario)
    sh = building.living_area_m2

    # Equivalent south-facing transparent surface (m2), constant across months in V1.
    sse = sum(w.area_m2 * w.solar_factor for w in building.windows)
    sse *= SOLAR_ORIENTATION_SHADING_COEFFICIENT

    w_setpoint = degree_hours_factor(scenario)

    needs: dict[int, float] = {}
    for month in _MONTHS:
        dh19 = _monthly(climate, "dh19_ch", zone, month)
        dh21 = _monthly(climate, "dh21_ch", zone, month)
        nref19 = _monthly(climate, "nref19_h", zone, month)
        nref21 = _monthly(climate, "nref21_h", zone, month)
        dh = dh19 + w_setpoint * (dh21 - dh19)
        nref = nref19 + w_setpoint * (nref21 - nref19)
        if dh <= 0.0 or nref <= 0.0:
            needs[month] = 0.0
            continue

        internal_wh = (p_equipment * sh + p_adult * occ_fraction * nadeq) * nref
        solar_wh = 1000.0 * sse * _monthly(climate, "e_kwh_m2", zone, month)
        x = (internal_wh + solar_wh) / (gv * dh)
        if x >= 1.0:
            needs[month] = 0.0
            continue
        f = (x - x**inertia_exp) / (1.0 - x**inertia_exp)
        needs[month] = gv * dh * (1.0 - f) / 1000.0
    return needs


def annual_needs(building: Building, scenario: OccupancyScenario) -> AnnualNeeds:
    """Annual heating and DHW needs (kWh), summing the monthly series."""
    heating = sum(monthly_heating_needs(building, scenario).values())
    dhw = sum(monthly_dhw_needs(building, scenario).values())
    return AnnualNeeds(heating_kwh=heating, dhw_kwh=dhw)
