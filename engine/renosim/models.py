"""Domain models for a single-family home, following the simplified 3CL-DPE 2021 method.

All dataclasses are immutable (``frozen=True``): renovation measures (see ``renovation.py``)
transform a :class:`Building` into a new one rather than mutating it in place.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ClimateZone(StrEnum):
    """DPE climate zone, per the conventional 3CL zoning of metropolitan France."""

    H1A = "H1a"
    H1B = "H1b"
    H1C = "H1c"
    H2A = "H2a"
    H2B = "H2b"
    H2C = "H2c"
    H2D = "H2d"
    H3 = "H3"


class AltitudeClass(StrEnum):
    """3CL altitude class, used alongside the climate zone for degree-hour lookups."""

    LOW = "low"  # < 400 m
    MEDIUM = "medium"  # 400-800 m
    HIGH = "high"  # > 800 m


class ConstructionPeriod(StrEnum):
    """Construction period bracket used to look up default U-values (table §5)."""

    BEFORE_1948 = "before_1948"
    Y1948_1974 = "1948_1974"
    Y1975_1977 = "1975_1977"
    Y1978_1982 = "1978_1982"
    Y1983_1988 = "1983_1988"
    Y1989_2000 = "1989_2000"
    Y2001_2005 = "2001_2005"
    Y2006_2012 = "2006_2012"
    AFTER_2013 = "after_2013"


class EnergyCarrier(StrEnum):
    """Final energy carrier, used for primary energy conversion and CO2 factors."""

    ELECTRICITY = "electricity"
    NATURAL_GAS = "natural_gas"
    FUEL_OIL = "fuel_oil"
    WOOD_LOGS = "wood_logs"
    WOOD_PELLETS = "wood_pellets"
    DISTRICT_HEATING = "district_heating"


class HeatingGeneratorType(StrEnum):
    """Space-heating generator type, used to look up conventional efficiencies/SCOP."""

    STANDARD_BOILER = "standard_boiler"
    LOW_TEMPERATURE_BOILER = "low_temperature_boiler"
    CONDENSING_BOILER = "condensing_boiler"
    ELECTRIC_JOULE = "electric_joule"
    HEAT_PUMP_AIR_WATER = "heat_pump_air_water"
    HEAT_PUMP_AIR_AIR = "heat_pump_air_air"
    WOOD_PELLET_STOVE = "wood_pellet_stove"
    WOOD_BOILER = "wood_boiler"
    DISTRICT_HEATING_SUBSTATION = "district_heating_substation"


class DHWGeneratorType(StrEnum):
    """Domestic hot water generator type."""

    ELECTRIC_STORAGE = "electric_storage"
    GAS_STORAGE_OR_INSTANT = "gas_storage_or_instant"
    HEAT_PUMP_WATER_HEATER = "heat_pump_water_heater"
    COUPLED_TO_HEATING_SYSTEM = "coupled_to_heating_system"


class VentilationType(StrEnum):
    """Ventilation system type, used to look up conventional airflow rates."""

    NATURAL = "natural"
    EXHAUST_ONLY_MANUAL = "exhaust_only_manual"  # VMC simple flux autoréglable
    EXHAUST_ONLY_HYGRO_A = "exhaust_only_hygro_a"  # VMC hygroréglable A
    EXHAUST_ONLY_HYGRO_B = "exhaust_only_hygro_b"  # VMC hygroréglable B
    BALANCED_HEAT_RECOVERY = "balanced_heat_recovery"  # VMC double flux


@dataclass(frozen=True, slots=True)
class OpaqueEnvelopeElement:
    """A single opaque envelope surface (wall, floor, roof) contributing to GV.

    Parameters
    ----------
    area_m2
        Surface area in square metres.
    u_value_w_per_m2k
        Thermal transmittance in W/(m2.K).
    unheated_space_reduction_coefficient
        The 3CL "b" coefficient (0-1) reducing losses for surfaces facing an unheated
        space rather than the outside; 1.0 for surfaces facing outside or the ground.
    """

    area_m2: float
    u_value_w_per_m2k: float
    unheated_space_reduction_coefficient: float = 1.0

    def __post_init__(self) -> None:
        if self.area_m2 <= 0:
            raise ValueError(f"area_m2 must be positive, got {self.area_m2}")
        if self.u_value_w_per_m2k <= 0:
            raise ValueError(f"u_value_w_per_m2k must be positive, got {self.u_value_w_per_m2k}")
        if not 0.0 <= self.unheated_space_reduction_coefficient <= 1.0:
            raise ValueError(
                "unheated_space_reduction_coefficient must be in [0, 1], got "
                f"{self.unheated_space_reduction_coefficient}"
            )


@dataclass(frozen=True, slots=True)
class Window:
    """A window or glazed door contributing to both GV and solar gains.

    Parameters
    ----------
    area_m2
        Surface area in square metres.
    u_value_w_per_m2k
        Thermal transmittance in W/(m2.K).
    solar_factor
        Solar heat gain coefficient (facteur solaire Sw), dimensionless in [0, 1].
    unheated_space_reduction_coefficient
        The 3CL "b" coefficient (0-1); 1.0 for windows facing outside.
    """

    area_m2: float
    u_value_w_per_m2k: float
    solar_factor: float
    unheated_space_reduction_coefficient: float = 1.0

    def __post_init__(self) -> None:
        if self.area_m2 <= 0:
            raise ValueError(f"area_m2 must be positive, got {self.area_m2}")
        if self.u_value_w_per_m2k <= 0:
            raise ValueError(f"u_value_w_per_m2k must be positive, got {self.u_value_w_per_m2k}")
        if not 0.0 <= self.solar_factor <= 1.0:
            raise ValueError(f"solar_factor must be in [0, 1], got {self.solar_factor}")
        if not 0.0 <= self.unheated_space_reduction_coefficient <= 1.0:
            raise ValueError(
                "unheated_space_reduction_coefficient must be in [0, 1], got "
                f"{self.unheated_space_reduction_coefficient}"
            )


@dataclass(frozen=True, slots=True)
class HeatingSystem:
    """Space-heating generator.

    Parameters
    ----------
    generator_type
        Type of heat generator, used to look up conventional efficiency/SCOP tables.
    energy_carrier
        Final energy carrier consumed by the generator.
    generator_age_years
        Age of the generator in years, used to select an efficiency bracket when the
        table distinguishes by age. ``None`` if unknown (a default bracket is used).
    """

    generator_type: HeatingGeneratorType
    energy_carrier: EnergyCarrier
    generator_age_years: float | None = None

    def __post_init__(self) -> None:
        if self.generator_age_years is not None and self.generator_age_years < 0:
            raise ValueError(f"generator_age_years must be >= 0, got {self.generator_age_years}")


@dataclass(frozen=True, slots=True)
class DHWSystem:
    """Domestic hot water generator.

    Parameters
    ----------
    generator_type
        Type of DHW generator.
    energy_carrier
        Final energy carrier consumed by the generator. Ignored when
        ``generator_type`` is :attr:`DHWGeneratorType.COUPLED_TO_HEATING_SYSTEM`, in
        which case the space-heating system's carrier applies.
    """

    generator_type: DHWGeneratorType
    energy_carrier: EnergyCarrier


@dataclass(frozen=True, slots=True)
class VentilationSystem:
    """Ventilation system.

    Parameters
    ----------
    ventilation_type
        Type of ventilation system, used to look up conventional airflow rates and,
        for balanced systems, heat recovery efficiency.
    """

    ventilation_type: VentilationType


@dataclass(frozen=True, slots=True)
class Building:
    """A single-family home described for the purpose of energy simulation.

    Parameters
    ----------
    living_area_m2
        Conventional living area (surface habitable) in square metres.
    construction_period
        Construction period bracket, used to look up default U-values when not
        otherwise specified on individual envelope elements.
    climate_zone
        DPE climate zone.
    altitude_class
        DPE altitude class.
    walls
        Opaque wall elements.
    roof
        Roof or attic floor element.
    floor
        Ground floor (plancher bas) element.
    windows
        Window and glazed door elements.
    heating_system
        Space-heating generator.
    dhw_system
        Domestic hot water generator.
    ventilation_system
        Ventilation system.
    number_of_occupants
        Household size, used for DHW needs in personalized mode (§4.2). Ignored in
        conventional mode, where DHW needs derive from ``living_area_m2``.
    """

    living_area_m2: float
    construction_period: ConstructionPeriod
    climate_zone: ClimateZone
    altitude_class: AltitudeClass
    walls: tuple[OpaqueEnvelopeElement, ...]
    roof: OpaqueEnvelopeElement
    floor: OpaqueEnvelopeElement
    windows: tuple[Window, ...]
    heating_system: HeatingSystem
    dhw_system: DHWSystem
    ventilation_system: VentilationSystem
    number_of_occupants: int | None = None

    def __post_init__(self) -> None:
        if self.living_area_m2 <= 0:
            raise ValueError(f"living_area_m2 must be positive, got {self.living_area_m2}")
        if not self.walls:
            raise ValueError("a Building must have at least one wall element")
        if not self.windows:
            raise ValueError("a Building must have at least one window element")
        if self.number_of_occupants is not None and self.number_of_occupants <= 0:
            raise ValueError(
                f"number_of_occupants must be positive, got {self.number_of_occupants}"
            )
