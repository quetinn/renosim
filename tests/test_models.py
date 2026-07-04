"""Tests for renosim.models: construction, validation, and immutability."""

from dataclasses import FrozenInstanceError

import pytest

from renosim.models import (
    AltitudeClass,
    Building,
    ClimateZone,
    ConstructionPeriod,
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


def make_reference_building(**overrides: object) -> Building:
    """A minimal valid Building, for reuse across tests."""
    defaults: dict[str, object] = {
        "living_area_m2": 100.0,
        "construction_period": ConstructionPeriod.Y1975_1977,
        "climate_zone": ClimateZone.H1A,
        "altitude_class": AltitudeClass.LOW,
        "walls": (OpaqueEnvelopeElement(area_m2=120.0, u_value_w_per_m2k=1.5),),
        "roof": OpaqueEnvelopeElement(area_m2=100.0, u_value_w_per_m2k=2.5),
        "floor": OpaqueEnvelopeElement(area_m2=100.0, u_value_w_per_m2k=1.5),
        "windows": (Window(area_m2=15.0, u_value_w_per_m2k=4.5, solar_factor=0.6),),
        "heating_system": HeatingSystem(
            generator_type=HeatingGeneratorType.STANDARD_BOILER,
            energy_carrier=EnergyCarrier.FUEL_OIL,
        ),
        "dhw_system": DHWSystem(
            generator_type=DHWGeneratorType.COUPLED_TO_HEATING_SYSTEM,
            energy_carrier=EnergyCarrier.FUEL_OIL,
        ),
        "ventilation_system": VentilationSystem(ventilation_type=VentilationType.NATURAL),
    }
    defaults.update(overrides)
    return Building(**defaults)  # type: ignore[arg-type]


def test_reference_building_constructs() -> None:
    building = make_reference_building()
    assert building.living_area_m2 == 100.0


def test_building_is_immutable() -> None:
    building = make_reference_building()
    with pytest.raises(FrozenInstanceError):
        building.living_area_m2 = 200.0  # type: ignore[misc]


@pytest.mark.parametrize(
    "field,value",
    [
        ("area_m2", 0.0),
        ("area_m2", -5.0),
        ("u_value_w_per_m2k", 0.0),
    ],
)
def test_opaque_element_rejects_invalid_values(field: str, value: float) -> None:
    kwargs = {"area_m2": 10.0, "u_value_w_per_m2k": 1.0}
    kwargs[field] = value
    with pytest.raises(ValueError, match="must be positive"):
        OpaqueEnvelopeElement(**kwargs)


def test_opaque_element_rejects_out_of_range_b_coefficient() -> None:
    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        OpaqueEnvelopeElement(
            area_m2=10.0, u_value_w_per_m2k=1.0, unheated_space_reduction_coefficient=1.5
        )


def test_window_rejects_out_of_range_solar_factor() -> None:
    with pytest.raises(ValueError, match="solar_factor"):
        Window(area_m2=2.0, u_value_w_per_m2k=1.5, solar_factor=1.2)


def test_heating_system_rejects_negative_age() -> None:
    with pytest.raises(ValueError, match="generator_age_years"):
        HeatingSystem(
            generator_type=HeatingGeneratorType.CONDENSING_BOILER,
            energy_carrier=EnergyCarrier.NATURAL_GAS,
            generator_age_years=-1,
        )


def test_building_requires_at_least_one_wall() -> None:
    with pytest.raises(ValueError, match="at least one wall"):
        make_reference_building(walls=())


def test_building_requires_at_least_one_window() -> None:
    with pytest.raises(ValueError, match="at least one window"):
        make_reference_building(windows=())


def test_building_rejects_non_positive_living_area() -> None:
    with pytest.raises(ValueError, match="living_area_m2"):
        make_reference_building(living_area_m2=0.0)


def test_building_rejects_non_positive_occupant_count() -> None:
    with pytest.raises(ValueError, match="number_of_occupants"):
        make_reference_building(number_of_occupants=0)
