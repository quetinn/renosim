"""End-to-end reference cases (CLAUDE.md §7.1) and cross-cutting invariants.

Expected labels are plausibility targets, not exact values: the engine is a
simplified 3CL and will be calibrated against the ADEME dataset in Phase 3.
"""

import pytest

from renosim import (
    AltitudeClass,
    Building,
    ClimateZone,
    ConstructionPeriod,
    DHWGeneratorType,
    DHWSystem,
    EnergyCarrier,
    HeatingGeneratorType,
    HeatingSystem,
    OccupancyScenario,
    OpaqueEnvelopeElement,
    VentilationSystem,
    VentilationType,
    Window,
    simulate,
)
from renosim.envelope import default_u_values


def house_1970_oil_uninsulated() -> Building:
    """~1970, 100 m2, uninsulated, old oil boiler, zone H1a — expected F-G."""
    u = default_u_values(
        ConstructionPeriod.Y1948_1974, ClimateZone.H1A, insulated=False, electric_joule=False
    )
    return Building(
        living_area_m2=100.0,
        construction_period=ConstructionPeriod.Y1948_1974,
        climate_zone=ClimateZone.H1A,
        altitude_class=AltitudeClass.LOW,
        walls=(OpaqueEnvelopeElement(area_m2=120.0, u_value_w_per_m2k=u.wall),),
        roof=OpaqueEnvelopeElement(area_m2=100.0, u_value_w_per_m2k=u.roof),
        floor=OpaqueEnvelopeElement(area_m2=100.0, u_value_w_per_m2k=u.floor),
        windows=(Window(area_m2=15.0, u_value_w_per_m2k=4.8, solar_factor=0.56),),
        heating_system=HeatingSystem(
            generator_type=HeatingGeneratorType.STANDARD_BOILER,
            energy_carrier=EnergyCarrier.FUEL_OIL,
            generator_age_years=50,
        ),
        dhw_system=DHWSystem(
            generator_type=DHWGeneratorType.COUPLED_TO_HEATING_SYSTEM,
            energy_carrier=EnergyCarrier.FUEL_OIL,
        ),
        ventilation_system=VentilationSystem(ventilation_type=VentilationType.NATURAL),
    )


def house_1970_renovated() -> Building:
    """Same house after full renovation: insulation + heat pump + hygro B VMC."""
    base = house_1970_oil_uninsulated()
    r_wall, r_roof = 3.7, 7.0
    new_wall_u = 1.0 / (1.0 / base.walls[0].u_value_w_per_m2k + r_wall)
    new_roof_u = 1.0 / (1.0 / base.roof.u_value_w_per_m2k + r_roof)
    return Building(
        living_area_m2=base.living_area_m2,
        construction_period=base.construction_period,
        climate_zone=base.climate_zone,
        altitude_class=base.altitude_class,
        walls=(OpaqueEnvelopeElement(area_m2=120.0, u_value_w_per_m2k=new_wall_u),),
        roof=OpaqueEnvelopeElement(area_m2=100.0, u_value_w_per_m2k=new_roof_u),
        floor=base.floor,
        windows=(Window(area_m2=15.0, u_value_w_per_m2k=1.4, solar_factor=0.43),),
        heating_system=HeatingSystem(
            generator_type=HeatingGeneratorType.HEAT_PUMP_AIR_WATER,
            energy_carrier=EnergyCarrier.ELECTRICITY,
            generator_age_years=1,
        ),
        dhw_system=DHWSystem(
            generator_type=DHWGeneratorType.HEAT_PUMP_WATER_HEATER,
            energy_carrier=EnergyCarrier.ELECTRICITY,
        ),
        ventilation_system=VentilationSystem(ventilation_type=VentilationType.EXHAUST_ONLY_HYGRO_B),
    )


def house_rt2012_heat_pump() -> Building:
    """RT2012-era 100 m2 house with a heat pump — expected A-C."""
    u = default_u_values(
        ConstructionPeriod.AFTER_2013, ClimateZone.H2B, insulated=True, electric_joule=False
    )
    return Building(
        living_area_m2=100.0,
        construction_period=ConstructionPeriod.AFTER_2013,
        climate_zone=ClimateZone.H2B,
        altitude_class=AltitudeClass.LOW,
        walls=(OpaqueEnvelopeElement(area_m2=110.0, u_value_w_per_m2k=u.wall),),
        roof=OpaqueEnvelopeElement(area_m2=100.0, u_value_w_per_m2k=u.roof),
        floor=OpaqueEnvelopeElement(area_m2=100.0, u_value_w_per_m2k=u.floor),
        windows=(Window(area_m2=18.0, u_value_w_per_m2k=1.4, solar_factor=0.43),),
        heating_system=HeatingSystem(
            generator_type=HeatingGeneratorType.HEAT_PUMP_AIR_WATER,
            energy_carrier=EnergyCarrier.ELECTRICITY,
            generator_age_years=5,
        ),
        dhw_system=DHWSystem(
            generator_type=DHWGeneratorType.HEAT_PUMP_WATER_HEATER,
            energy_carrier=EnergyCarrier.ELECTRICITY,
        ),
        ventilation_system=VentilationSystem(ventilation_type=VentilationType.EXHAUST_ONLY_HYGRO_B),
    )


def house_gas_1990_h2() -> Building:
    """1989-2000, 120 m2, gas boiler, zone H2a — typical D-E."""
    u = default_u_values(
        ConstructionPeriod.Y1989_2000, ClimateZone.H2A, insulated=True, electric_joule=False
    )
    return Building(
        living_area_m2=120.0,
        construction_period=ConstructionPeriod.Y1989_2000,
        climate_zone=ClimateZone.H2A,
        altitude_class=AltitudeClass.LOW,
        walls=(OpaqueEnvelopeElement(area_m2=130.0, u_value_w_per_m2k=u.wall),),
        roof=OpaqueEnvelopeElement(area_m2=120.0, u_value_w_per_m2k=u.roof),
        floor=OpaqueEnvelopeElement(area_m2=120.0, u_value_w_per_m2k=u.floor),
        windows=(Window(area_m2=20.0, u_value_w_per_m2k=2.8, solar_factor=0.5),),
        heating_system=HeatingSystem(
            generator_type=HeatingGeneratorType.STANDARD_BOILER,
            energy_carrier=EnergyCarrier.NATURAL_GAS,
            generator_age_years=30,
        ),
        dhw_system=DHWSystem(
            generator_type=DHWGeneratorType.COUPLED_TO_HEATING_SYSTEM,
            energy_carrier=EnergyCarrier.NATURAL_GAS,
        ),
        ventilation_system=VentilationSystem(ventilation_type=VentilationType.EXHAUST_ONLY_MANUAL),
    )


def small_house_electric() -> Building:
    """Edge case: 35 m2 house, electric heating (thresholds <40 m2 not modelled)."""
    u = default_u_values(
        ConstructionPeriod.Y1975_1977, ClimateZone.H1B, insulated=True, electric_joule=True
    )
    return Building(
        living_area_m2=35.0,
        construction_period=ConstructionPeriod.Y1975_1977,
        climate_zone=ClimateZone.H1B,
        altitude_class=AltitudeClass.LOW,
        walls=(OpaqueEnvelopeElement(area_m2=60.0, u_value_w_per_m2k=u.wall),),
        roof=OpaqueEnvelopeElement(area_m2=35.0, u_value_w_per_m2k=u.roof),
        floor=OpaqueEnvelopeElement(area_m2=35.0, u_value_w_per_m2k=u.floor),
        windows=(Window(area_m2=6.0, u_value_w_per_m2k=2.8, solar_factor=0.5),),
        heating_system=HeatingSystem(
            generator_type=HeatingGeneratorType.ELECTRIC_JOULE,
            energy_carrier=EnergyCarrier.ELECTRICITY,
        ),
        dhw_system=DHWSystem(
            generator_type=DHWGeneratorType.ELECTRIC_STORAGE,
            energy_carrier=EnergyCarrier.ELECTRICITY,
        ),
        ventilation_system=VentilationSystem(ventilation_type=VentilationType.NATURAL),
    )


# ---------------------------------------------------------------- reference cases


def test_case_1970_oil_house_is_f_or_g() -> None:
    result = simulate(house_1970_oil_uninsulated())
    assert result.label in ("F", "G"), (result.label, result.primary_energy_kwh_m2)
    assert result.primary_energy_kwh_m2 > 330


def test_case_renovated_house_reaches_c_to_d_with_60pct_savings() -> None:
    # CLAUDE.md §7.1: full renovation bundle -> "C-D attendu, économies > 60 %"
    before = simulate(house_1970_oil_uninsulated())
    after = simulate(house_1970_renovated())
    assert after.label in ("B", "C", "D"), (after.label, after.primary_energy_kwh_m2)
    savings = 1.0 - after.final_energy_kwh_m2 / before.final_energy_kwh_m2
    assert savings > 0.6, savings


def test_case_rt2012_heat_pump_is_a_to_c() -> None:
    result = simulate(house_rt2012_heat_pump())
    assert result.label in ("A", "B", "C"), (result.label, result.primary_energy_kwh_m2)


def test_case_gas_1990_house_is_c_to_e() -> None:
    result = simulate(house_gas_1990_h2())
    assert result.label in ("C", "D", "E"), (result.label, result.primary_energy_kwh_m2)


def test_case_small_house_runs_and_uses_standard_thresholds() -> None:
    # <40 m2 surface-dependent thresholds (arrêté 25/03/2024) are NOT modelled;
    # documented deviation — the engine must still produce a coherent result.
    result = simulate(small_house_electric())
    assert result.label in ("A", "B", "C", "D", "E", "F", "G")
    assert result.final_energy_kwh_m2 > 0


# ---------------------------------------------------------------------- invariants


def test_invariant_positive_consumption() -> None:
    for factory in (
        house_1970_oil_uninsulated,
        house_1970_renovated,
        house_rt2012_heat_pump,
        house_gas_1990_h2,
        small_house_electric,
    ):
        result = simulate(factory())
        assert result.final_energy_kwh_m2 > 0
        assert result.primary_energy_kwh_m2 > 0
        assert result.co2_kg_m2 > 0
        assert result.annual_cost_eur > 0


def test_invariant_label_only_from_conventional_run() -> None:
    result = simulate(house_gas_1990_h2(), OccupancyScenario(heating_setpoint_c=21.0))
    assert result.is_conventional is False
    conventional = simulate(house_gas_1990_h2())
    assert conventional.is_conventional is True


def test_invariant_personalized_setpoint_monotonic() -> None:
    building = house_gas_1990_h2()
    cold = simulate(building, OccupancyScenario(heating_setpoint_c=17.0))
    conv = simulate(building)
    warm = simulate(building, OccupancyScenario(heating_setpoint_c=21.0))
    assert cold.final_energy_kwh_m2 < conv.final_energy_kwh_m2 < warm.final_energy_kwh_m2


def test_invariant_2026_vintage_lowers_electric_primary_energy() -> None:
    building = house_rt2012_heat_pump()
    ep_2021 = simulate(building, regulation_vintage="dpe_2021").primary_energy_kwh_m2
    ep_2026 = simulate(building, regulation_vintage="dpe_2026").primary_energy_kwh_m2
    assert ep_2026 == pytest.approx(ep_2021 * 1.9 / 2.3, rel=1e-6)
