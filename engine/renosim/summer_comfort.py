"""Passive summer-comfort indicator (annexe 9 of the DPE 2021 arrêté, #16 brique 1).

Qualitative three-level assessment (insufficient / medium / good) of the
dwelling's ability to remain comfortable during hot spells WITHOUT active
cooling, implemented verbatim from annexe 9 §1.2 (see
``tables/summer_comfort.json`` for the sourced decision grid). It is displayed
NEXT TO the winter DPE label and never merged with it: a dwelling can be both
label A and an oven in a heat wave — surfacing that asymmetry is the point.

The indicator involves no energy calculation and no occupancy scenario: it is
a pure function of the building description.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from renosim.models import Building, InertiaClass, SolarProtectionLevel
from renosim.tables_io import load_table


class SummerComfortLevel(StrEnum):
    """The three official levels of the passive summer-comfort indicator."""

    INSUFFICIENT = "insufficient"
    MEDIUM = "medium"
    GOOD = "good"


@dataclass(frozen=True, slots=True)
class SummerComfortAssessment:
    """Passive summer-comfort level with the individual criteria behind it.

    The criteria let the UI list the favourable assets ("toiture isolée",
    "logement traversant"...) and the annexe 9 §3 improvement recommendations.

    Parameters
    ----------
    level
        Official three-level indicator value.
    roof_criterion_applicable
        False for an apartment without a deperditive ceiling (ground floor or
        intermediate storey), where the roof-insulation criterion is skipped
        per annexe 9 §1.2.
    roof_insulated
        Resolved roof-insulation state (declared, or the official annexe 9
        default by construction period when unknown). Only meaningful when
        ``roof_criterion_applicable`` is True.
    solar_protections_full
        True when every S/E/W/roof bay has an exterior solar protection.
    heavy_inertia
        True when the dwelling inertia is heavy (official criterion: "lourde
        ou très lourde").
    through_dwelling
        Resolved through-dwelling state (declared, or derived per D-19).
    fixed_air_circulators
        True when the dwelling has fixed ceiling/wall fans.
    """

    level: SummerComfortLevel
    roof_criterion_applicable: bool
    roof_insulated: bool
    solar_protections_full: bool
    heavy_inertia: bool
    through_dwelling: bool
    fixed_air_circulators: bool


def assess_summer_comfort(building: Building) -> SummerComfortAssessment:
    """Assess the passive summer-comfort level of a dwelling (annexe 9 §1.2).

    Parameters
    ----------
    building
        Building description; the summer-specific fields
        (``exterior_solar_protections``, ``has_fixed_air_circulators``,
        ``roof_insulated``, ``through_dwelling``) have safe defaults.

    Returns
    -------
    SummerComfortAssessment
        Level plus the individual criteria for display.
    """
    table = load_table("summer_comfort")

    # Roof criterion skipped without a deperditive ceiling (annexe 9 §1.2):
    # apartments on an intermediate storey model their ceiling with b = 0.
    roof_applicable = building.roof.unheated_space_reduction_coefficient > 0.0
    if building.roof_insulated is not None:
        roof_insulated = building.roof_insulated
    else:
        uninsulated_periods = frozenset(table["unknown_roof_default"]["uninsulated_periods"])
        roof_insulated = building.construction_period.value not in uninsulated_periods

    # UNKNOWN protections are treated as FULL (deviation D-19).
    solar_full = building.exterior_solar_protections in (
        SolarProtectionLevel.FULL,
        SolarProtectionLevel.UNKNOWN,
    )

    heavy_inertia = building.inertia is InertiaClass.HEAVY
    if building.through_dwelling is not None:
        through = building.through_dwelling
    else:
        through = not building.single_exposed_facade
    fans = building.has_fixed_air_circulators

    insufficient = (not solar_full) or (roof_applicable and not roof_insulated)
    favourable_count = sum((heavy_inertia, through, fans))
    if insufficient:
        level = SummerComfortLevel.INSUFFICIENT
    elif favourable_count >= int(table["good_level_min_favourable_criteria"]):
        level = SummerComfortLevel.GOOD
    else:
        level = SummerComfortLevel.MEDIUM

    return SummerComfortAssessment(
        level=level,
        roof_criterion_applicable=roof_applicable,
        roof_insulated=roof_insulated,
        solar_protections_full=solar_full,
        heavy_inertia=heavy_inertia,
        through_dwelling=through,
        fixed_air_circulators=fans,
    )


__all__ = [
    "SummerComfortAssessment",
    "SummerComfortLevel",
    "assess_summer_comfort",
]
