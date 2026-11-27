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
    #: Wood-log stove, insert, closed fireplace or cooker (3CL §13.1).
    WOOD_LOG_STOVE = "wood_log_stove"
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


class GlazingOrientation(StrEnum):
    """Dominant orientation of the glazed areas (simplified journey input).

    Modulates the solar gains with the 3CL C1 orientation ratios (§18.5);
    ``UNKNOWN`` means balanced/unknown glazing and applies no modifier, which
    reproduces the calibrated deviation D-06 behaviour.
    """

    SOUTH = "south"
    EAST_WEST = "east_west"
    NORTH = "north"
    UNKNOWN = "unknown"


class SolarShading(StrEnum):
    """Simplified distant-mask level, mapped onto the 3CL Fe2 factors (§6.2.2.2.1).

    ``CLEAR_OR_UNKNOWN`` applies no reduction (the calibrated solar coefficient
    already embeds an average masking level); ``PARTIAL`` matches obstacles of
    15-30°, ``HEAVY`` obstacles of 30-60°.
    """

    CLEAR_OR_UNKNOWN = "clear_or_unknown"
    PARTIAL = "partial"
    HEAVY = "heavy"


class SolarProtectionLevel(StrEnum):
    """Exterior solar protections of the bays facing South, East, West or roof.

    Annexe 9 of the DPE arrêté (passive summer-comfort indicator): the level
    is "insufficient" as soon as one such bay lacks an exterior protection
    (shutters, external blinds, BSO...). The guided form asks the user
    directly instead of collecting per-bay data (deviation D-19);
    ``UNKNOWN`` is treated as ``FULL`` (protections are directly observable,
    the default only serves the pressed user).
    """

    FULL = "full"
    PARTIAL = "partial"
    NONE = "none"
    UNKNOWN = "unknown"


class CoolingPeriod(StrEnum):
    """Installation period of the cooling generator, selecting the SEER bracket.

    3CL §10.3 SEER table; ``UNKNOWN`` maps to the most recent bracket
    (documented convention D-20 — the French residential AC stock is
    overwhelmingly recent).
    """

    BEFORE_2008 = "before_2008"
    Y2008_2014 = "2008_2014"
    FROM_2015 = "from_2015"
    UNKNOWN = "unknown"


class DwellingType(StrEnum):
    """Dwelling type: single-family house (V1) or apartment (V1.1, #15).

    Selects the collective variants of the conventional tables: Nadeq
    (3CL §11.1), Q4Pa-conv airtightness (§4), ventilation auxiliaries (§5)
    and the intermittence I0 table (§8).
    """

    HOUSE = "house"
    APARTMENT = "apartment"


class InertiaClass(StrEnum):
    """Thermal inertia class selecting the 3CL utilization-factor exponent (§6.1).

    The official method derives the class from the wall/floor composition; the
    simplified journey asks a single question instead. ``UNKNOWN`` keeps the
    Phase 3 calibrated behaviour (medium inertia, deviation D-14).
    """

    LIGHT = "light"
    MEDIUM = "medium"
    HEAVY = "heavy"
    UNKNOWN = "unknown"


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
    installed_after_2012
        True when the system was installed after 2012 (e.g. by a renovation
        measure): the recent conventional airflow/auxiliary brackets then apply
        regardless of the building construction period.
    """

    ventilation_type: VentilationType
    installed_after_2012: bool = False


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
    glazing_orientation
        Dominant orientation of the glazed areas; ``UNKNOWN`` (default) applies no
        solar-orientation modifier.
    solar_shading
        Simplified distant-mask level; ``CLEAR_OR_UNKNOWN`` (default) applies no
        reduction.
    inertia
        Thermal inertia class for the utilization-factor exponent; ``UNKNOWN``
        (default) behaves as medium inertia (deviation D-14).
    dwelling_type
        House (default) or apartment; apartments use the collective variants
        of the conventional tables (D-18).
    single_exposed_facade
        True for a non-through apartment (one facade to the outside): the
        infiltration shelter coefficients e/f switch to the "une seule facade
        exposee" column (3CL §4).
    exterior_solar_protections
        Exterior solar protections of the S/E/W/roof bays, for the passive
        summer-comfort indicator (annexe 9, #16 brique 1).
    has_fixed_air_circulators
        True when the dwelling has FIXED ceiling/wall fans (brasseurs d'air
        fixes; mobile fans do not count, annexe 9 §1.2).
    has_air_conditioning
        True when the dwelling has an active cooling system: its conventional
        consumption Cfr (3CL §10) is then part of the assessed uses (D-02
        lifted, #16 brique 2). The cooling NEED Bfr is computed either way.
    air_conditioning_period
        Installation period of the cooling generator (SEER bracket, §10.3).
        Ignored when ``has_air_conditioning`` is False.
    roof_insulated
        Declared insulation state of the roof/cover for the summer-comfort
        indicator; ``None`` (unknown) applies the official annexe 9 default
        (considered insulated from 1975 onwards).
    through_dwelling
        Whether the dwelling is through-oriented (openings on opposite
        facades); ``None`` derives it: houses are assumed through, apartments
        use ``single_exposed_facade`` (deviation D-19).
    ceiling_height_m
        Average ceiling height Hsp in metres, used by the intermittence factor
        (3CL §8, G = GV/(Hsp*Sh)); it cancels out of the §4 infiltration
        formula. ``None`` (default) applies the conventional height.
    heating_backup
        Wood-log stove, insert or pellet stove used as a back-up of the main
        heating (3CL §9.3): it covers 25 % of the heating need, the main system
        75 %. ``None`` (default): the main system covers everything.
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
    glazing_orientation: GlazingOrientation = GlazingOrientation.UNKNOWN
    solar_shading: SolarShading = SolarShading.CLEAR_OR_UNKNOWN
    inertia: InertiaClass = InertiaClass.UNKNOWN
    dwelling_type: DwellingType = DwellingType.HOUSE
    single_exposed_facade: bool = False
    exterior_solar_protections: SolarProtectionLevel = SolarProtectionLevel.UNKNOWN
    has_fixed_air_circulators: bool = False
    has_air_conditioning: bool = False
    air_conditioning_period: CoolingPeriod = CoolingPeriod.UNKNOWN
    roof_insulated: bool | None = None
    through_dwelling: bool | None = None
    ceiling_height_m: float | None = None
    heating_backup: HeatingSystem | None = None

    def __post_init__(self) -> None:
        if self.living_area_m2 <= 0:
            raise ValueError(f"living_area_m2 must be positive, got {self.living_area_m2}")
        if not self.walls:
            raise ValueError("a Building must have at least one wall element")
        if not self.windows:
            raise ValueError("a Building must have at least one window element")
        if self.ceiling_height_m is not None and self.ceiling_height_m <= 0:
            raise ValueError(f"ceiling_height_m must be positive, got {self.ceiling_height_m}")
        if self.heating_backup is not None and self.heating_backup.generator_type not in (
            HeatingGeneratorType.WOOD_LOG_STOVE,
            HeatingGeneratorType.WOOD_PELLET_STOVE,
        ):
            raise ValueError(
                "heating_backup must be a wood-log or pellet stove/insert (3CL §9.3), got "
                f"{self.heating_backup.generator_type.value}"
            )
        if self.number_of_occupants is not None and self.number_of_occupants <= 0:
            raise ValueError(
                f"number_of_occupants must be positive, got {self.number_of_occupants}"
            )
