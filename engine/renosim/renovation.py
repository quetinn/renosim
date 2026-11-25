"""Renovation measures: immutable Building -> Building transformations.

Each of the six V1 measures (CLAUDE.md §2.1) is a frozen dataclass with an
``apply`` method returning a NEW :class:`Building`. Bundles are applied in the
canonical order envelope -> ventilation -> systems (§4.3): the new heating
system is thus evaluated on the post-insulation building. Savings of a bundle
are NOT the sum of individual savings (interactions) — a pedagogical point
surfaced in the app.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from typing import Protocol

from renosim.models import (
    Building,
    DHWGeneratorType,
    DHWSystem,
    EnergyCarrier,
    HeatingGeneratorType,
    HeatingSystem,
    OpaqueEnvelopeElement,
    SolarProtectionLevel,
    VentilationSystem,
    VentilationType,
    Window,
)
from renosim.systems import HYDRAULIC_GENERATORS
from renosim.tables_io import load_table

#: Default added thermal resistances (m2.K/W), usual "performant" levels
#: (CLAUDE.md §4.3): R=7 for roof/attic, R=3.7 for walls.
DEFAULT_ROOF_ADDED_R = 7.0
DEFAULT_WALL_ADDED_R = 3.7

#: Carrier implied by each replacement generator type.
_GENERATOR_CARRIER = {
    HeatingGeneratorType.HEAT_PUMP_AIR_WATER: EnergyCarrier.ELECTRICITY,
    HeatingGeneratorType.HEAT_PUMP_AIR_AIR: EnergyCarrier.ELECTRICITY,
    HeatingGeneratorType.CONDENSING_BOILER: EnergyCarrier.NATURAL_GAS,
    HeatingGeneratorType.WOOD_PELLET_STOVE: EnergyCarrier.WOOD_PELLETS,
}


class RenovationMeasure(Protocol):
    """A renovation measure: pure transformation of a building description."""

    @property
    def order(self) -> int:
        """Sort key: 0 = envelope, 1 = ventilation, 2 = heat systems."""
        ...

    @property
    def cost_key(self) -> str:
        """Key into tables/renovation_costs.json (see economics.py)."""
        ...

    def apply(self, building: Building) -> Building:
        """Return a new Building with the measure applied."""
        ...


def added_r_from_insulation(material: str, thickness_cm: float) -> float:
    """Added thermal resistance of an insulation layer: R = thickness / lambda.

    Parameters
    ----------
    material
        Key into ``tables/insulation_materials.json`` (e.g. ``"glass_wool"``);
        ``"unknown"`` applies the 3CL conventional lambda of 0.04 W/(m.K).
    thickness_cm
        Insulation thickness in centimetres (> 0).

    Returns
    -------
    float
        Added thermal resistance in m2.K/W.
    """
    materials = load_table("insulation_materials")["materials"]
    if material not in materials:
        known = ", ".join(sorted(materials))
        raise ValueError(f"unknown insulation material {material!r} (expected one of: {known})")
    if thickness_cm <= 0:
        raise ValueError(f"thickness_cm must be positive, got {thickness_cm}")
    lambda_w_per_mk = float(materials[material]["lambda_w_per_mk"])
    return (thickness_cm / 100.0) / lambda_w_per_mk


def _insulate(element: OpaqueEnvelopeElement, added_r: float) -> OpaqueEnvelopeElement:
    """New element with added insulation: U' = 1 / (1/U + delta_R)."""
    new_u = 1.0 / (1.0 / element.u_value_w_per_m2k + added_r)
    return replace(element, u_value_w_per_m2k=new_u)


@dataclass(frozen=True, slots=True)
class WallInsulation:
    """Wall insulation (ITI/ITE undistinguished in V1, deviation D-04).

    Parameters
    ----------
    added_r_m2k_per_w
        Added thermal resistance in m2.K/W (default 3.7, usual performant level).
    """

    added_r_m2k_per_w: float = DEFAULT_WALL_ADDED_R
    order: int = 0
    cost_key: str = "wall_insulation"

    def apply(self, building: Building) -> Building:
        walls = tuple(_insulate(w, self.added_r_m2k_per_w) for w in building.walls)
        return replace(building, walls=walls)


@dataclass(frozen=True, slots=True)
class RoofInsulation:
    """Roof / attic insulation.

    Parameters
    ----------
    added_r_m2k_per_w
        Added thermal resistance in m2.K/W (default 7, usual performant level).
    """

    added_r_m2k_per_w: float = DEFAULT_ROOF_ADDED_R
    order: int = 0
    cost_key: str = "roof_insulation"

    def apply(self, building: Building) -> Building:
        # An insulated roof also flips the summer-comfort roof criterion
        # (annexe 9): dual winter/summer effect of the measure (#16).
        return replace(
            building,
            roof=_insulate(building.roof, self.added_r_m2k_per_w),
            roof_insulated=True,
        )


@dataclass(frozen=True, slots=True)
class WindowReplacement:
    """Window replacement to a better glazing (defaults from the U tables).

    Parameters
    ----------
    glazing
        Key of ``window_defaults`` in tables/u_values_default.json
        (e.g. ``"double_glazing_low_e"``, ``"triple_glazing"``).
    """

    glazing: str = "double_glazing_low_e"
    order: int = 0
    cost_key: str = "window_replacement"

    def apply(self, building: Building) -> Building:
        defaults = load_table("u_values_default")["window_defaults"][self.glazing]
        new_u = float(defaults["u_w_per_m2k"])
        new_sw = float(defaults["solar_factor"])
        windows = tuple(
            Window(
                area_m2=w.area_m2,
                u_value_w_per_m2k=new_u,
                solar_factor=new_sw,
                unheated_space_reduction_coefficient=w.unheated_space_reduction_coefficient,
            )
            for w in building.windows
        )
        return replace(building, windows=windows)


@dataclass(frozen=True, slots=True)
class VentilationUpgrade:
    """Install or replace the mechanical ventilation system.

    The new system uses the post-2012 conventional airflow and auxiliary-power
    brackets. Note: a balanced system (double flux) lowers Hvent a lot but
    consumes more auxiliary electricity — both effects are modelled.
    """

    new_type: VentilationType = VentilationType.EXHAUST_ONLY_HYGRO_B
    order: int = 1
    cost_key: str = "vmc_hygro_b"

    def __post_init__(self) -> None:
        if self.new_type is VentilationType.BALANCED_HEAT_RECOVERY:
            object.__setattr__(self, "cost_key", "vmc_double_flux")

    def apply(self, building: Building) -> Building:
        return replace(
            building,
            ventilation_system=VentilationSystem(
                ventilation_type=self.new_type, installed_after_2012=True
            ),
        )


@dataclass(frozen=True, slots=True)
class HeatingReplacement:
    """Replace the space-heating generator (matrix per CLAUDE.md §2.1).

    The new generator's energy carrier is implied by its type; its age is 0 so
    the most recent efficiency/SCOP brackets apply.
    """

    new_generator: HeatingGeneratorType = HeatingGeneratorType.HEAT_PUMP_AIR_WATER
    order: int = 2
    cost_key: str = "heat_pump_air_water"

    def __post_init__(self) -> None:
        keys = {
            HeatingGeneratorType.HEAT_PUMP_AIR_WATER: "heat_pump_air_water",
            HeatingGeneratorType.CONDENSING_BOILER: "condensing_gas_boiler",
            HeatingGeneratorType.WOOD_PELLET_STOVE: "wood_pellet_stove",
        }
        if self.new_generator not in keys:
            raise ValueError(
                f"unsupported replacement generator: {self.new_generator} "
                "(V1 matrix: heat pump air-water, condensing gas boiler, pellet stove)"
            )
        object.__setattr__(self, "cost_key", keys[self.new_generator])

    def apply(self, building: Building) -> Building:
        carrier = _GENERATOR_CARRIER[self.new_generator]
        new_system = HeatingSystem(
            generator_type=self.new_generator,
            energy_carrier=carrier,
            generator_age_years=0.0,
        )
        new_building = replace(building, heating_system=new_system)
        if building.dhw_system.generator_type is not DHWGeneratorType.COUPLED_TO_HEATING_SYSTEM:
            return new_building
        if self.new_generator in HYDRAULIC_GENERATORS:
            # DHW coupled to the heating system follows the new generator's carrier.
            new_dhw = DHWSystem(
                generator_type=DHWGeneratorType.COUPLED_TO_HEATING_SYSTEM,
                energy_carrier=carrier,
            )
        else:
            # A generator without hydraulic network (pellet stove) cannot produce
            # DHW: the coupled production moves to an electric storage water
            # heater (audit 2026-11-25, §4.1). An explicit DHWUpgrade in the same
            # bundle still overrides it, whatever the order.
            new_dhw = DHWSystem(
                generator_type=DHWGeneratorType.ELECTRIC_STORAGE,
                energy_carrier=EnergyCarrier.ELECTRICITY,
            )
        return replace(new_building, dhw_system=new_dhw)


@dataclass(frozen=True, slots=True)
class SolarProtectionInstallation:
    """Install exterior solar protections (volets/BSO) on every bay (#16 brique 3).

    A pure summer measure: it lifts the annexe 9 "insufficient" condition of
    the passive summer-comfort indicator. No effect on V1 consumptions —
    mobile protections are outside the 3CL cooling-need calculation (D-19).
    """

    order: int = 0
    cost_key: str = "solar_protection_installation"

    def apply(self, building: Building) -> Building:
        return replace(building, exterior_solar_protections=SolarProtectionLevel.FULL)


@dataclass(frozen=True, slots=True)
class DHWUpgrade:
    """Switch DHW to a heat-pump water heater (chauffe-eau thermodynamique)."""

    order: int = 2
    cost_key: str = "heat_pump_water_heater"

    def apply(self, building: Building) -> Building:
        return replace(
            building,
            dhw_system=DHWSystem(
                generator_type=DHWGeneratorType.HEAT_PUMP_WATER_HEATER,
                energy_carrier=EnergyCarrier.ELECTRICITY,
            ),
        )


#: Factories producing one default-parameter instance of each measure (the six
#: V1 energy measures plus the summer-only solar protections, #16 brique 3),
#: used by invariant tests and by the app's measure cards.
ALL_MEASURE_FACTORIES: tuple[Callable[[], RenovationMeasure], ...] = (
    WallInsulation,
    RoofInsulation,
    WindowReplacement,
    VentilationUpgrade,
    HeatingReplacement,
    DHWUpgrade,
    SolarProtectionInstallation,
)


def apply_measures(building: Building, measures: Sequence[RenovationMeasure]) -> Building:
    """Apply a bundle of measures in the canonical envelope-first order.

    Parameters
    ----------
    building
        Starting building (never mutated).
    measures
        Measures in any order; they are sorted envelope (0) -> ventilation (1)
        -> systems (2) before sequential application.

    Returns
    -------
    Building
        New building with all measures applied.
    """
    result = building
    for measure in sorted(measures, key=lambda m: m.order):
        result = measure.apply(result)
    return result


def predefined_bundles() -> dict[str, tuple[RenovationMeasure, ...]]:
    """The app's predefined bundles (CLAUDE.md §6.2)."""
    return {
        "enveloppe_d_abord": (WallInsulation(), RoofInsulation(), WindowReplacement()),
        "sortie_du_fioul": (
            HeatingReplacement(new_generator=HeatingGeneratorType.HEAT_PUMP_AIR_WATER),
            DHWUpgrade(),
        ),
        "renovation_globale": (
            WallInsulation(),
            RoofInsulation(),
            WindowReplacement(),
            VentilationUpgrade(),
            HeatingReplacement(new_generator=HeatingGeneratorType.HEAT_PUMP_AIR_WATER),
            DHWUpgrade(),
        ),
    }
