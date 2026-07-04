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
    VentilationSystem,
    VentilationType,
    Window,
)
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
        return replace(building, roof=_insulate(building.roof, self.added_r_m2k_per_w))


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
        # DHW coupled to the heating system follows the new generator's carrier.
        if building.dhw_system.generator_type is DHWGeneratorType.COUPLED_TO_HEATING_SYSTEM:
            new_building = replace(
                new_building,
                dhw_system=DHWSystem(
                    generator_type=DHWGeneratorType.COUPLED_TO_HEATING_SYSTEM,
                    energy_carrier=carrier,
                ),
            )
        return new_building


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


#: Factories producing one default-parameter instance of each of the 6 measures,
#: used by invariant tests and by the app's measure cards.
ALL_MEASURE_FACTORIES: tuple[Callable[[], RenovationMeasure], ...] = (
    WallInsulation,
    RoofInsulation,
    WindowReplacement,
    VentilationUpgrade,
    HeatingReplacement,
    DHWUpgrade,
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
