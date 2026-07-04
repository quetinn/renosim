"""Envelope heat losses: GV = surface losses + thermal bridges + air renewal.

Follows 3CL-DPE 2021 §3 (parois) and §4 (ventilation/infiltration) with the
documented V1 simplifications: flat thermal-bridge surcharge instead of linear
metres x psi (docs/deviations.md D-03), and a single b coefficient carried by
each envelope element.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import cast

from renosim.models import Building, ClimateZone, ConstructionPeriod, VentilationType
from renosim.tables_io import load_table

#: V1 flat thermal-bridge surcharge applied to surface losses (deviation D-03).
#: Candidate for calibration against the ADEME dataset in Phase 3.
THERMAL_BRIDGE_SURCHARGE = 0.08

#: Default average ceiling height (m), used for infiltration and intermittence.
DEFAULT_CEILING_HEIGHT_M = 2.5


@dataclass(frozen=True, slots=True)
class EnvelopeLosses:
    """Breakdown of the envelope heat-loss coefficient (all in W/K).

    ``gv_w_per_k`` is the total: surface + thermal bridges + ventilation +
    infiltration.
    """

    walls_w_per_k: float
    roof_w_per_k: float
    floor_w_per_k: float
    windows_w_per_k: float
    thermal_bridges_w_per_k: float
    ventilation_w_per_k: float
    infiltration_w_per_k: float

    @property
    def surface_w_per_k(self) -> float:
        """Surface (transmission) losses through opaque and glazed elements."""
        return self.walls_w_per_k + self.roof_w_per_k + self.floor_w_per_k + self.windows_w_per_k

    @property
    def gv_w_per_k(self) -> float:
        """Total envelope heat-loss coefficient GV."""
        return (
            self.surface_w_per_k
            + self.thermal_bridges_w_per_k
            + self.ventilation_w_per_k
            + self.infiltration_w_per_k
        )


@dataclass(frozen=True, slots=True)
class DefaultUValues:
    """Default U-values (W/(m2.K)) resolved from the 3CL lookup tables."""

    wall: float
    roof: float
    floor: float


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

_ZONE_GROUP = {
    ClimateZone.H1A: "H1",
    ClimateZone.H1B: "H1",
    ClimateZone.H1C: "H1",
    ClimateZone.H2A: "H2",
    ClimateZone.H2B: "H2",
    ClimateZone.H2C: "H2",
    ClimateZone.H2D: "H2",
    ClimateZone.H3: "H3",
}


def default_u_values(
    period: ConstructionPeriod,
    zone: ClimateZone,
    *,
    insulated: bool,
    electric_joule: bool,
) -> DefaultUValues:
    """Default U-values for walls, roof (combles) and floor per the 3CL tables.

    Parameters
    ----------
    period
        Construction period bracket.
    zone
        DPE climate zone (collapsed onto H1/H2/H3 groups for the lookup).
    insulated
        Whether the element is insulated (at an unknown date). Per 3CL, a
        pre-1975 construction insulated at an unknown date uses the 75-77 row.
    electric_joule
        Whether the dwelling is heated by direct electric (joule) — the tables
        distinguish it.

    Returns
    -------
    DefaultUValues
        Wall, roof and floor default U in W/(m2.K).
    """
    table = load_table("u_values_default")
    if not insulated:
        base = table["uninsulated_defaults"]
        return DefaultUValues(
            wall=float(base["wall_u_nu"]),
            roof=float(base["roof_u0"]),
            floor=float(base["floor_u0"]),
        )

    period_key = _PERIOD_KEY[period]
    if period in (ConstructionPeriod.BEFORE_1948, ConstructionPeriod.Y1948_1974):
        # 3CL rule: pre-1975 construction insulated at unknown date -> 75-77 row.
        period_key = "1975_1977"
    group = _ZONE_GROUP[zone]
    heat = "joule" if electric_joule else "others"

    wall = float(table["wall_insulated_by_period"][group][heat][period_key])
    roof = float(table["roof_insulated_by_period"]["combles"][group][heat][period_key])
    floor = float(table["floor_insulated_by_period"][group][heat][period_key])
    return DefaultUValues(wall=wall, roof=roof, floor=floor)


def _q4pa_conv_per_m2(period: ConstructionPeriod) -> float:
    """Conventional envelope airtightness Q4Pa-conv/m2 for a house, per period."""
    table = load_table("ventilation")["q4pa_conv_house_by_period"]
    if period in (ConstructionPeriod.BEFORE_1948,):
        return float(table["before_1948"])
    if period is ConstructionPeriod.Y1948_1974:
        return float(table["1948_1974"])
    if period in (
        ConstructionPeriod.Y1975_1977,
        ConstructionPeriod.Y1978_1982,
        ConstructionPeriod.Y1983_1988,
        ConstructionPeriod.Y1989_2000,
        ConstructionPeriod.Y2001_2005,
    ):
        return float(table["1975_2005"])
    if period is ConstructionPeriod.Y2006_2012:
        return float(table["2006_2012"])
    return float(table["after_2012"])


def conventional_airflows(building: Building) -> tuple[float, float, float]:
    """Conventional airflow rates (Qvarep, Qvasouf, Smea) for the building.

    The installation-period bracket of the ventilation system is approximated
    by the construction period (V1 simplification: the guided journey does not
    ask for the ventilation installation year separately).

    Returns
    -------
    tuple[float, float, float]
        ``(qvarep, qvasouf, smea)`` in m3/(h.m2).
    """
    airflow = load_table("ventilation")["airflow_by_type"]
    vtype = building.ventilation_system.ventilation_type
    period = building.construction_period
    installed_recent = building.ventilation_system.installed_after_2012

    def bracket(entry: dict[str, object], *keys: str) -> dict[str, float]:
        for key in keys:
            if key in entry:
                return cast(dict[str, float], entry[key])
        raise KeyError(f"no bracket {keys} in ventilation table")

    if vtype is VentilationType.NATURAL:
        e = airflow["natural"]
        return float(e["qvarep"]), float(e["qvasouf"]), float(e["smea"])

    recent = installed_recent or period in (
        ConstructionPeriod.Y2006_2012,
        ConstructionPeriod.AFTER_2013,
    )
    if vtype is VentilationType.EXHAUST_ONLY_MANUAL:
        entry = airflow["exhaust_only_manual"]
        if installed_recent or period is ConstructionPeriod.AFTER_2013:
            b = bracket(entry, "after_2012")
        elif period is ConstructionPeriod.Y2006_2012 or period is ConstructionPeriod.Y2001_2005:
            b = bracket(entry, "2001_2012")
        elif period in (ConstructionPeriod.Y1983_1988, ConstructionPeriod.Y1989_2000):
            b = bracket(entry, "1982_2000")
        else:
            b = bracket(entry, "before_1982")
    elif vtype is VentilationType.EXHAUST_ONLY_HYGRO_A:
        entry = airflow["exhaust_only_hygro_a"]
        if recent:
            b = bracket(entry, "after_2012")
        elif period in (ConstructionPeriod.Y2001_2005,):
            b = bracket(entry, "2001_2012")
        else:
            b = bracket(entry, "before_2001")
    elif vtype is VentilationType.EXHAUST_ONLY_HYGRO_B:
        entry = airflow["exhaust_only_hygro_b"]
        if recent:
            b = bracket(entry, "after_2012")
        elif period is ConstructionPeriod.Y2001_2005:
            b = bracket(entry, "2001_2012")
        else:
            b = bracket(entry, "before_2001")
    elif vtype is VentilationType.BALANCED_HEAT_RECOVERY:
        entry = airflow["balanced_heat_recovery"]
        b = bracket(
            entry,
            "after_2012"
            if installed_recent or period is ConstructionPeriod.AFTER_2013
            else "before_2012",
        )
    else:  # pragma: no cover - exhaustive over VentilationType
        raise ValueError(f"unsupported ventilation type: {vtype}")

    return float(b["qvarep"]), float(b["qvasouf"]), float(b["smea"])


def envelope_heat_loss(building: Building) -> EnvelopeLosses:
    """Compute the envelope heat-loss breakdown and total GV (W/K).

    Surface losses: sum of U*A*b over walls, roof, floor and windows (3CL §3).
    Thermal bridges: flat surcharge (deviation D-03). Air renewal: Hvent =
    0.34*Qvarep*Sh and Hperm from the conventional airtightness (3CL §4).

    Parameters
    ----------
    building
        Building description with resolved U-values.

    Returns
    -------
    EnvelopeLosses
        Loss breakdown; ``gv_w_per_k`` is the total GV.
    """
    walls = sum(
        w.u_value_w_per_m2k * w.area_m2 * w.unheated_space_reduction_coefficient
        for w in building.walls
    )
    roof = (
        building.roof.u_value_w_per_m2k
        * building.roof.area_m2
        * building.roof.unheated_space_reduction_coefficient
    )
    floor = (
        building.floor.u_value_w_per_m2k
        * building.floor.area_m2
        * building.floor.unheated_space_reduction_coefficient
    )
    windows = sum(
        w.u_value_w_per_m2k * w.area_m2 * w.unheated_space_reduction_coefficient
        for w in building.windows
    )
    surface = walls + roof + floor + windows
    bridges = THERMAL_BRIDGE_SURCHARGE * surface

    qvarep, qvasouf, smea = conventional_airflows(building)
    sh = building.living_area_m2
    hvent = 0.34 * qvarep * sh

    # Infiltration (3CL §4): n50 from conventional Q4Pa, wind exposure e/f.
    shelter = load_table("ventilation")["shelter_coefficients"]["several_exposed_facades"]
    e_coef, f_coef = float(shelter["e"]), float(shelter["f"])
    hsp = DEFAULT_CEILING_HEIGHT_M
    sdep = (
        sum(w.area_m2 for w in building.walls)
        + building.roof.area_m2
        + sum(w.area_m2 for w in building.windows)
    )
    q4pa_env = _q4pa_conv_per_m2(building.construction_period) * sdep
    q4pa = q4pa_env + 0.45 * smea * sh
    n50 = q4pa / ((4.0 / 50.0) ** (2.0 / 3.0) * hsp * sh)
    unbalance = (qvasouf - qvarep) / (hsp * n50)
    qvinf = hsp * sh * n50 * e_coef / math.sqrt(1.0 + (f_coef / e_coef) * unbalance**2)
    hperm = 0.34 * qvinf

    return EnvelopeLosses(
        walls_w_per_k=walls,
        roof_w_per_k=roof,
        floor_w_per_k=floor,
        windows_w_per_k=windows,
        thermal_bridges_w_per_k=bridges,
        ventilation_w_per_k=hvent,
        infiltration_w_per_k=hperm,
    )
