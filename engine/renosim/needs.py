"""Heating, cooling and DHW needs, monthly, per the simplified 3CL-DPE 2021 chain.

Heating (3CL §6/§9): ``Bch_j = GV * (1 - F_j) * DH_j / 1000`` [kWh] with the
free-gains utilization factor ``F_j`` from the gains/losses ratio and inertia.
Recovered generation/storage losses are ignored (deviation D-07).

Cooling (3CL §10.2, #16 brique 2): the summer mirror of the heating chain —
gains become the load and envelope exchanges the relief:
``Bfr_j = (Ai_fr_j + As_fr_j)/1000 - fut_j * GV/1000 * (Tint - Text_clim_j) * Nref_j``
with ``(Tint - Text_clim_j) * Nref_j = -DH28_j`` (the tabulated cooling
degree-hours) and the utilization factor ``fut`` from the inverse balance
ratio and the §10.2 time constant. Computed with the conventional 28 degC
setpoint whatever the occupancy scenario (D-20).

DHW (3CL §11.1): ``Becs_j = 1.163 * Nadeq * V * (40 - Tefs_j) * nj_j / 1000``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from renosim.envelope import envelope_heat_loss
from renosim.models import AltitudeClass, Building, GlazingOrientation, InertiaClass
from renosim.occupancy import OccupancyScenario, degree_hours_factor, equivalent_adults
from renosim.tables_io import load_table

#: Base orientation+shading coefficient applied to window solar apertures when
#: building the equivalent south surface (deviation D-06: absolute level
#: calibrated against the ADEME base in Phase 3). When the user declares a
#: dominant glazing orientation or explicit distant masks, this base is
#: modulated by :func:`solar_orientation_modifier` (3CL C1 ratios, §18.5) and
#: :func:`solar_shading_factor` (3CL Fe2, §6.2.2.2.1); the neutral defaults
#: reproduce the calibrated behaviour exactly.
SOLAR_ORIENTATION_SHADING_COEFFICIENT = float(
    load_table("conventions")["calibrated"]["solar_orientation_shading_coefficient"]["value"]
)

_ALTITUDE_KEY = {
    AltitudeClass.LOW: "low",
    AltitudeClass.MEDIUM: "medium",
    AltitudeClass.HIGH: "high",
}

_MONTHS = tuple(range(1, 13))

#: Key into utilization_factor_inertia_exponents (3CL §6.1) per inertia class;
#: UNKNOWN keeps the calibrated V1 default (medium, deviation D-14).
_INERTIA_EXPONENT_KEY = {
    InertiaClass.LIGHT: "light",
    InertiaClass.MEDIUM: "medium",
    InertiaClass.HEAVY: "heavy_very_heavy",
    InertiaClass.UNKNOWN: "medium",
}


@dataclass(frozen=True, slots=True)
class AnnualNeeds:
    """Annual useful energy needs (kWh), before system efficiencies.

    ``cooling_kwh`` is the conventional cooling need Bfr (28 degC setpoint):
    a physical indicator computed for every dwelling — it only becomes a
    consumption when an air conditioner is declared (systems.py).
    """

    heating_kwh: float
    dhw_kwh: float
    cooling_kwh: float = 0.0


def _climate(building: Building) -> dict[str, dict[str, dict[str, float]]]:
    table = load_table("climate_zones")
    return cast(
        dict[str, dict[str, dict[str, float]]], table[_ALTITUDE_KEY[building.altitude_class]]
    )


def _monthly(
    climate: dict[str, dict[str, dict[str, float]]], series: str, zone: str, month: int
) -> float:
    return float(climate[series][zone][str(month)])


def solar_orientation_modifier(building: Building) -> float:
    """Solar-gain modifier for the dominant glazing orientation.

    Ratio of the heating-season vertical C1 of the declared orientation to the
    mean of the four orientations (tables/solar_orientation.json, from 3CL
    §18.5). ``UNKNOWN`` returns 1.0 (balanced glazing, calibrated D-06 level).
    """
    orientation = building.glazing_orientation
    if orientation is GlazingOrientation.UNKNOWN:
        return 1.0
    c1 = load_table("solar_orientation")["c1_heating_season_vertical"]
    zone = c1[building.climate_zone.value]
    south, west = float(zone["south"]), float(zone["west"])
    north, east = float(zone["north"]), float(zone["east"])
    mean = (south + west + north + east) / 4.0
    if orientation is GlazingOrientation.SOUTH:
        return south / mean
    if orientation is GlazingOrientation.NORTH:
        return north / mean
    return (east + west) / 2.0 / mean


def solar_shading_factor(building: Building) -> float:
    """Distant-mask reduction factor Fe2 (tables/solar_orientation.json)."""
    factors = load_table("solar_orientation")["shading_factors"]
    return float(factors[building.solar_shading.value])


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
    nadeq = equivalent_adults(building.living_area_m2, scenario, building.dwelling_type)
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
    (deviation D-06). Utilization factor F from the X ratio and the exponent
    of the building's declared inertia class (medium when unknown, D-14).

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
    inertia_exp = float(
        occupancy["utilization_factor_inertia_exponents"][_INERTIA_EXPONENT_KEY[building.inertia]]
    )

    climate = _climate(building)
    zone = building.climate_zone.value
    gv = envelope_heat_loss(building).gv_w_per_k
    nadeq = equivalent_adults(building.living_area_m2, scenario, building.dwelling_type)
    sh = building.living_area_m2

    # Equivalent south-facing transparent surface (m2), constant across months in V1.
    sse = sum(w.area_m2 * w.solar_factor for w in building.windows)
    sse *= (
        SOLAR_ORIENTATION_SHADING_COEFFICIENT
        * solar_orientation_modifier(building)
        * solar_shading_factor(building)
    )

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


def summer_solar_orientation_coefficient(building: Building) -> float:
    """Cooling-season solar coefficient of the glazed apertures (D-06/D-20).

    The calibrated winter coefficient (0.5) embeds an effective shading level
    times the heating-season average vertical C1; the summer variant keeps the
    same effective level and swaps in the official cooling-season C1 of the
    declared orientation (§18.5, June-September vertical average):
    ``0.5 * C1_summer[orientation] / mean_vertical_C1_winter[zone]``.
    ``UNKNOWN`` uses the mean of the four summer orientations.
    """
    table = load_table("solar_orientation")
    zone = building.climate_zone.value
    summer = table["c1_cooling_season_vertical"][zone]
    winter_mean = float(table["c1_heating_season_vertical_mean"][zone])
    orientation = building.glazing_orientation
    if orientation is GlazingOrientation.SOUTH:
        c1 = float(summer["south"])
    elif orientation is GlazingOrientation.NORTH:
        c1 = float(summer["north"])
    elif orientation is GlazingOrientation.EAST_WEST:
        c1 = (float(summer["east"]) + float(summer["west"])) / 2.0
    else:
        c1 = (
            float(summer["south"])
            + float(summer["west"])
            + float(summer["north"])
            + float(summer["east"])
        ) / 4.0
    return SOLAR_ORIENTATION_SHADING_COEFFICIENT * c1 / winter_mean


def monthly_cooling_needs(building: Building, scenario: OccupancyScenario) -> dict[int, float]:
    """Monthly conventional cooling needs Bfr_j in kWh (3CL §10.2).

    Always evaluated with the conventional 28 degC cooling setpoint (D-20).
    Internal gains reuse the §6.1 conventional powers over the Nref(28)
    cooling hours; solar gains use E_fr(28) and the summer C1 coefficient.
    The balance ratio ``Rbth = gains / (GV * DH28)`` gates the need (no need
    below 1/2) and drives the §10.2 utilization factor.

    Returns
    -------
    dict[int, float]
        Needs in kWh keyed by month 1-12 (0 outside the cooling season).
    """
    occupancy = load_table("occupancy_conventional")
    gains_cfg = occupancy["internal_gains"]
    p_equipment = float(gains_cfg["equipment_plus_lighting_w_per_m2"])
    p_adult = float(gains_cfg["per_adult_w"])
    occ_fraction = float(gains_cfg["occupancy_fraction"])

    cooling = load_table("cooling")
    cin_per_m2 = cooling["internal_heat_capacity_j_per_k_m2"]
    inertia_key = {"light": "light", "medium": "medium", "heavy": "heavy"}.get(
        building.inertia.value, "medium"
    )
    cin = float(cin_per_m2[inertia_key]) * building.living_area_m2

    climate = _climate(building)
    zone = building.climate_zone.value
    gv = envelope_heat_loss(building).gv_w_per_k
    nadeq = equivalent_adults(building.living_area_m2, scenario, building.dwelling_type)
    sh = building.living_area_m2

    sse_fr = sum(w.area_m2 * w.solar_factor for w in building.windows)
    sse_fr *= summer_solar_orientation_coefficient(building) * solar_shading_factor(building)

    time_constant_h = cin / (3600.0 * gv)
    a = 1.0 + time_constant_h / 15.0

    needs: dict[int, float] = {}
    for month in _MONTHS:
        nref = _monthly(climate, "nref28_fr_h", zone, month)
        dh28 = _monthly(climate, "dh28_fr_ch", zone, month)
        if nref <= 0.0 or dh28 <= 0.0:
            needs[month] = 0.0
            continue
        internal_wh = (p_equipment * sh + p_adult * occ_fraction * nadeq) * nref
        solar_wh = 1000.0 * sse_fr * _monthly(climate, "e_fr28_kwh_m2", zone, month)
        gains_wh = internal_wh + solar_wh
        rbth = gains_wh / (gv * dh28)
        if rbth < 0.5:
            needs[month] = 0.0
            continue
        fut = a / (a + 1.0) if rbth == 1.0 else (1.0 - rbth**-a) / (1.0 - rbth ** (-a - 1.0))
        # (Tint - Text_clim) * Nref = -DH28: the envelope inflow term.
        needs[month] = gains_wh / 1000.0 + fut * gv * dh28 / 1000.0
    return needs


def annual_heating_hours(building: Building, scenario: OccupancyScenario) -> float:
    """Annual heating-season hours Nref (h), setpoint-interpolated like DH.

    Used by the §15.2.2 heating-circulator consumption (Caux_dist_ch =
    Pcirc x Nref).
    """
    climate = _climate(building)
    zone = building.climate_zone.value
    w_setpoint = degree_hours_factor(scenario)
    total = 0.0
    for month in _MONTHS:
        nref19 = _monthly(climate, "nref19_h", zone, month)
        nref21 = _monthly(climate, "nref21_h", zone, month)
        total += max(0.0, nref19 + w_setpoint * (nref21 - nref19))
    return total


def annual_needs(building: Building, scenario: OccupancyScenario) -> AnnualNeeds:
    """Annual heating, DHW and cooling needs (kWh), summing the monthly series."""
    heating = sum(monthly_heating_needs(building, scenario).values())
    dhw = sum(monthly_dhw_needs(building, scenario).values())
    cooling = sum(monthly_cooling_needs(building, scenario).values())
    return AnnualNeeds(heating_kwh=heating, dhw_kwh=dhw, cooling_kwh=cooling)
