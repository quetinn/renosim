"""Occupancy scenarios: the conventional DPE scenario and user-personalized variants.

A single :class:`OccupancyScenario` object is injected through the whole calculation
chain; the conventional mode is just a frozen instance of it (CLAUDE.md §4.2). The
displayed DPE label must ALWAYS come from a run with :data:`CONVENTIONAL`.
"""

from __future__ import annotations

from dataclasses import dataclass

from renosim.tables_io import load_table

#: Bounds accepted for a personalized heating setpoint (degC). The conventional
#: climate tables provide DH19/DH21; outside this range the linear DH scaling
#: between those two anchors loses credibility.
MIN_SETPOINT_C = 16.0
MAX_SETPOINT_C = 23.0


@dataclass(frozen=True, slots=True)
class OccupancyScenario:
    """Occupancy assumptions injected into the calculation chain.

    Parameters
    ----------
    heating_setpoint_c
        Heating setpoint in degrees Celsius. Conventional DPE value: 19.
    dhw_liters_per_day_per_adult
        Hot water draw-off at 40 degC, litres per equivalent adult per day.
        Conventional DPE value: 56.
    occupants_override
        If set (personalized mode), replaces the conventional equivalent-adult
        count derived from the living area for DHW and internal gains.
    is_conventional
        True only for the frozen conventional scenario; the DPE label shown to
        the user must come from a conventional run.
    """

    heating_setpoint_c: float = 19.0
    dhw_liters_per_day_per_adult: float = 56.0
    occupants_override: float | None = None
    is_conventional: bool = False

    def __post_init__(self) -> None:
        if not MIN_SETPOINT_C <= self.heating_setpoint_c <= MAX_SETPOINT_C:
            raise ValueError(
                f"heating_setpoint_c must be in [{MIN_SETPOINT_C}, {MAX_SETPOINT_C}], "
                f"got {self.heating_setpoint_c}"
            )
        if self.dhw_liters_per_day_per_adult <= 0:
            raise ValueError("dhw_liters_per_day_per_adult must be positive")
        if self.occupants_override is not None and self.occupants_override <= 0:
            raise ValueError("occupants_override must be positive")
        if self.is_conventional and (
            self.heating_setpoint_c != 19.0
            or self.dhw_liters_per_day_per_adult != 56.0
            or self.occupants_override is not None
        ):
            raise ValueError("the conventional scenario cannot carry personalized values")


#: The frozen conventional DPE scenario (3CL: 19 degC, 56 l/day/adult, Nadeq from area).
CONVENTIONAL = OccupancyScenario(is_conventional=True)


def equivalent_adults(living_area_m2: float, scenario: OccupancyScenario) -> float:
    """Number of equivalent adults (Nadeq) for DHW needs and internal gains.

    Follows 3CL-DPE 2021 §11.1 for a single-family house (Nblgt = 1) in
    conventional mode; in personalized mode the user-provided occupant count is
    used directly.

    Parameters
    ----------
    living_area_m2
        Living area (surface habitable) in square metres.
    scenario
        Active occupancy scenario.

    Returns
    -------
    float
        Equivalent adults (dimensionless).
    """
    if scenario.occupants_override is not None:
        return scenario.occupants_override

    # Constants from tables/occupancy_conventional.json (§11.1); the formulas are
    # structural to the method, the table documents their source.
    _ = load_table("occupancy_conventional")
    sh_moy = living_area_m2  # Nblgt = 1 for a single-family house
    if sh_moy < 30.0:
        n_max = 1.0
    elif sh_moy < 70.0:
        n_max = 1.75 - 0.01875 * (70.0 - sh_moy)
    else:
        n_max = 0.025 * sh_moy

    if n_max < 1.75:
        return n_max
    return 1.75 + 0.3 * (n_max - 1.75)


def degree_hours_factor(scenario: OccupancyScenario) -> float:
    """Interpolation weight of the setpoint between the DH19 and DH21 tables.

    The 3CL climate tables provide degree-hours for 19 degC (conventional) and
    21 degC (spendthrift) setpoints. For a personalized setpoint T the engine
    interpolates/extrapolates linearly: ``DH(T) = DH19 + w * (DH21 - DH19)``
    with ``w = (T - 19) / 2``. Conventional mode returns 0 exactly.

    Returns
    -------
    float
        Weight ``w`` (0 for 19 degC, 1 for 21 degC; may be negative below 19).
    """
    return (scenario.heating_setpoint_c - 19.0) / 2.0
