"""Tests for the passive summer-comfort indicator (annexe 9, #16 brique 1).

Expected levels are derived by hand from the annexe 9 §1.2 grid:

- insufficient <=> at least one S/E/W/roof bay without exterior protection,
  OR deperditive ceiling with an uninsulated roof;
- good <=> not insufficient AND >= 2 of {heavy inertia, through, fixed fans};
- medium otherwise.

Unknown roof state: uninsulated before 1975, insulated from 1975 (official
default). Unknown protections are treated as full and houses as through
(deviation D-19).
"""

from dataclasses import replace

from renosim.models import (
    AltitudeClass,
    Building,
    ClimateZone,
    ConstructionPeriod,
    DHWGeneratorType,
    DHWSystem,
    DwellingType,
    EnergyCarrier,
    HeatingGeneratorType,
    HeatingSystem,
    InertiaClass,
    OpaqueEnvelopeElement,
    SolarProtectionLevel,
    VentilationSystem,
    VentilationType,
    Window,
)
from renosim.renovation import RoofInsulation
from renosim.summer_comfort import SummerComfortLevel, assess_summer_comfort


def make_building(**overrides: object) -> Building:
    """100 m2 house, 1989-2000, protections declared full unless overridden."""
    defaults: dict[str, object] = {
        "living_area_m2": 100.0,
        "construction_period": ConstructionPeriod.Y1989_2000,
        "climate_zone": ClimateZone.H1A,
        "altitude_class": AltitudeClass.LOW,
        "walls": (OpaqueEnvelopeElement(area_m2=80.0, u_value_w_per_m2k=0.5),),
        "roof": OpaqueEnvelopeElement(area_m2=100.0, u_value_w_per_m2k=0.3),
        "floor": OpaqueEnvelopeElement(area_m2=100.0, u_value_w_per_m2k=0.5),
        "windows": (Window(area_m2=16.7, u_value_w_per_m2k=2.7, solar_factor=0.6),),
        "heating_system": HeatingSystem(
            HeatingGeneratorType.STANDARD_BOILER, EnergyCarrier.NATURAL_GAS, 10.0
        ),
        "dhw_system": DHWSystem(
            DHWGeneratorType.COUPLED_TO_HEATING_SYSTEM, EnergyCarrier.NATURAL_GAS
        ),
        "ventilation_system": VentilationSystem(VentilationType.EXHAUST_ONLY_MANUAL),
        "exterior_solar_protections": SolarProtectionLevel.FULL,
    }
    defaults.update(overrides)
    return Building(**defaults)  # type: ignore[arg-type]


class TestInsufficientConditions:
    def test_missing_solar_protections_is_insufficient(self) -> None:
        for level in (SolarProtectionLevel.PARTIAL, SolarProtectionLevel.NONE):
            b = make_building(exterior_solar_protections=level)
            assert assess_summer_comfort(b).level is SummerComfortLevel.INSUFFICIENT

    def test_pre_1975_unknown_roof_is_insufficient(self) -> None:
        # Official default: roof considered uninsulated before 1975.
        b = make_building(construction_period=ConstructionPeriod.Y1948_1974)
        assessment = assess_summer_comfort(b)
        assert assessment.roof_insulated is False
        assert assessment.level is SummerComfortLevel.INSUFFICIENT

    def test_post_1975_unknown_roof_is_not_insufficient(self) -> None:
        b = make_building(construction_period=ConstructionPeriod.Y1975_1977)
        assessment = assess_summer_comfort(b)
        assert assessment.roof_insulated is True
        assert assessment.level is not SummerComfortLevel.INSUFFICIENT

    def test_declared_roof_state_overrides_period_default(self) -> None:
        insulated_old = make_building(
            construction_period=ConstructionPeriod.BEFORE_1948, roof_insulated=True
        )
        assert assess_summer_comfort(insulated_old).level is not SummerComfortLevel.INSUFFICIENT
        uninsulated_recent = make_building(roof_insulated=False)
        assert assess_summer_comfort(uninsulated_recent).level is SummerComfortLevel.INSUFFICIENT


class TestGoodAndMediumLevels:
    def test_through_house_alone_is_medium(self) -> None:
        # Houses are through by default (D-19): 1 favourable criterion only.
        assert assess_summer_comfort(make_building()).level is SummerComfortLevel.MEDIUM

    def test_two_favourable_criteria_reach_good(self) -> None:
        b = make_building(inertia=InertiaClass.HEAVY)  # heavy + through = 2
        assert assess_summer_comfort(b).level is SummerComfortLevel.GOOD

    def test_fans_and_through_reach_good(self) -> None:
        b = make_building(has_fixed_air_circulators=True)
        assert assess_summer_comfort(b).level is SummerComfortLevel.GOOD

    def test_favourable_criteria_do_not_rescue_insufficient(self) -> None:
        b = make_building(
            inertia=InertiaClass.HEAVY,
            has_fixed_air_circulators=True,
            exterior_solar_protections=SolarProtectionLevel.NONE,
        )
        assert assess_summer_comfort(b).level is SummerComfortLevel.INSUFFICIENT

    def test_non_through_house_with_medium_inertia_is_medium(self) -> None:
        b = make_building(through_dwelling=False, inertia=InertiaClass.MEDIUM)
        assert assess_summer_comfort(b).level is SummerComfortLevel.MEDIUM

    def test_unknown_protections_treated_as_full(self) -> None:
        b = make_building(exterior_solar_protections=SolarProtectionLevel.UNKNOWN)
        assert assess_summer_comfort(b).solar_protections_full is True
        assert assess_summer_comfort(b).level is SummerComfortLevel.MEDIUM


class TestApartmentCeilingRule:
    def test_intermediate_apartment_skips_roof_criterion(self) -> None:
        # Ceiling to a heated dwelling (b = 0): the roof criterion is skipped
        # even for a pre-1975 building (annexe 9 §1.2).
        b = make_building(
            construction_period=ConstructionPeriod.Y1948_1974,
            dwelling_type=DwellingType.APARTMENT,
            roof=OpaqueEnvelopeElement(
                area_m2=60.0, u_value_w_per_m2k=2.5, unheated_space_reduction_coefficient=0.0
            ),
            through_dwelling=False,
            single_exposed_facade=True,
        )
        assessment = assess_summer_comfort(b)
        assert assessment.roof_criterion_applicable is False
        assert assessment.level is SummerComfortLevel.MEDIUM

    def test_top_floor_apartment_keeps_roof_criterion(self) -> None:
        b = make_building(
            construction_period=ConstructionPeriod.Y1948_1974,
            dwelling_type=DwellingType.APARTMENT,
            roof=OpaqueEnvelopeElement(area_m2=60.0, u_value_w_per_m2k=2.5),
        )
        assert assess_summer_comfort(b).level is SummerComfortLevel.INSUFFICIENT

    def test_mono_oriented_apartment_is_not_through(self) -> None:
        b = make_building(
            dwelling_type=DwellingType.APARTMENT,
            roof=OpaqueEnvelopeElement(
                area_m2=60.0, u_value_w_per_m2k=2.5, unheated_space_reduction_coefficient=0.0
            ),
            single_exposed_facade=True,
        )
        assert assess_summer_comfort(b).through_dwelling is False


class TestRenovationInteraction:
    def test_roof_insulation_measure_lifts_insufficient(self) -> None:
        # 1950s house, unknown roof -> insufficient; insulating the roof both
        # lowers U and flips the summer criterion -> medium.
        before = make_building(construction_period=ConstructionPeriod.Y1948_1974)
        after = RoofInsulation().apply(before)
        assert after.roof_insulated is True
        assert assess_summer_comfort(before).level is SummerComfortLevel.INSUFFICIENT
        assert assess_summer_comfort(after).level is SummerComfortLevel.MEDIUM

    def test_assessment_never_worsens_with_roof_insulation(self) -> None:
        order = list(SummerComfortLevel)
        for period in ConstructionPeriod:
            before = make_building(construction_period=period)
            after = RoofInsulation().apply(before)
            assert order.index(assess_summer_comfort(after).level) >= order.index(
                assess_summer_comfort(before).level
            )

    def test_apply_does_not_mutate_source(self) -> None:
        before = make_building(construction_period=ConstructionPeriod.Y1948_1974)
        RoofInsulation().apply(before)
        assert before.roof_insulated is None
        assert replace(before).roof_insulated is None
