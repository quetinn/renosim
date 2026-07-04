"""Tests for renosim.renovation — measures, bundles, and CLAUDE.md §7.1 invariants."""

import pytest

from renosim import simulate
from renosim.models import (
    Building,
    DHWGeneratorType,
    EnergyCarrier,
    HeatingGeneratorType,
    VentilationType,
)
from renosim.renovation import (
    ALL_MEASURE_FACTORIES,
    DHWUpgrade,
    HeatingReplacement,
    RenovationMeasure,
    RoofInsulation,
    VentilationUpgrade,
    WallInsulation,
    WindowReplacement,
    apply_measures,
)
from tests.test_reference_cases import house_1970_oil_uninsulated


def _heating_needs(building: Building) -> float:
    return simulate(building).needs.heating_kwh


def test_measures_are_immutable_transformations() -> None:
    base = house_1970_oil_uninsulated()
    wall_u_before = base.walls[0].u_value_w_per_m2k
    renovated = WallInsulation().apply(base)
    assert base.walls[0].u_value_w_per_m2k == wall_u_before  # original untouched
    assert renovated is not base
    assert renovated.walls[0].u_value_w_per_m2k < wall_u_before


def test_wall_insulation_hand_computed_u() -> None:
    # U_before = 2.5, added R = 3.7 -> U_after = 1/(1/2.5 + 3.7) = 0.2439
    base = house_1970_oil_uninsulated()
    renovated = WallInsulation(added_r_m2k_per_w=3.7).apply(base)
    assert renovated.walls[0].u_value_w_per_m2k == pytest.approx(1.0 / (1.0 / 2.5 + 3.7))


def test_roof_insulation_default_r7() -> None:
    base = house_1970_oil_uninsulated()
    renovated = RoofInsulation().apply(base)
    assert renovated.roof.u_value_w_per_m2k == pytest.approx(1.0 / (1.0 / 2.5 + 7.0))


def test_window_replacement_changes_u_and_solar_factor() -> None:
    base = house_1970_oil_uninsulated()
    renovated = WindowReplacement(glazing="double_glazing_low_e").apply(base)
    assert renovated.windows[0].u_value_w_per_m2k == 1.4
    assert renovated.windows[0].solar_factor == 0.43
    assert renovated.windows[0].area_m2 == base.windows[0].area_m2


def test_heating_replacement_resets_age_and_carrier() -> None:
    base = house_1970_oil_uninsulated()
    renovated = HeatingReplacement(new_generator=HeatingGeneratorType.HEAT_PUMP_AIR_WATER).apply(
        base
    )
    assert renovated.heating_system.generator_type is HeatingGeneratorType.HEAT_PUMP_AIR_WATER
    assert renovated.heating_system.energy_carrier is EnergyCarrier.ELECTRICITY
    assert renovated.heating_system.generator_age_years == 0.0


def test_ventilation_upgrade_uses_recent_brackets() -> None:
    base = house_1970_oil_uninsulated()
    renovated = VentilationUpgrade(new_type=VentilationType.BALANCED_HEAT_RECOVERY).apply(base)
    assert renovated.ventilation_system.installed_after_2012 is True
    # double flux after 2012: Hvent = 0.34*0.26*100 = 8.84 W/K
    assert simulate(renovated).envelope.ventilation_w_per_k == pytest.approx(8.84)


def test_invariant_each_measure_never_increases_heating_needs() -> None:
    base = house_1970_oil_uninsulated()
    needs_before = _heating_needs(base)
    for factory in ALL_MEASURE_FACTORIES:
        measure = factory()
        needs_after = _heating_needs(measure.apply(base))
        assert needs_after <= needs_before + 1e-9, type(measure).__name__


def test_invariant_bundle_at_least_as_good_as_best_single_measure() -> None:
    base = house_1970_oil_uninsulated()
    measures: list[RenovationMeasure] = [
        WallInsulation(),
        RoofInsulation(),
        WindowReplacement(),
        HeatingReplacement(new_generator=HeatingGeneratorType.HEAT_PUMP_AIR_WATER),
    ]
    ep_singles = [simulate(apply_measures(base, [m])).primary_energy_kwh_m2 for m in measures]
    ep_bundle = simulate(apply_measures(base, measures)).primary_energy_kwh_m2
    assert ep_bundle <= min(ep_singles) + 1e-9


def test_bundle_savings_are_not_additive() -> None:
    """Non-additivity (CLAUDE.md §4.3): bundle savings != sum of single savings.

    Interactions pull in both directions: lower GV raises the free-gains
    coverage F (dampens savings) but also raises the intermittence factor INT
    (amplifies them, per the official INT = I0/(1+0.1(G-1)) formula). On a very
    leaky house the INT effect dominates and the bundle is super-additive.
    """
    base = house_1970_oil_uninsulated()
    ep_before = simulate(base).primary_energy_kwh_m2
    envelope_measures: list[RenovationMeasure] = [
        WallInsulation(),
        RoofInsulation(),
        WindowReplacement(),
    ]
    individual_savings = sum(
        ep_before - simulate(apply_measures(base, [m])).primary_energy_kwh_m2
        for m in envelope_measures
    )
    bundle_savings = (
        ep_before - simulate(apply_measures(base, envelope_measures)).primary_energy_kwh_m2
    )
    # materially different (> 2 %), in either direction
    assert abs(bundle_savings - individual_savings) > 0.02 * individual_savings


def test_apply_measures_orders_envelope_before_systems() -> None:
    base = house_1970_oil_uninsulated()
    # order given systems-first: apply_measures must still produce the same
    # result as envelope-first (transformations commute in V1, but the API
    # guarantees the canonical order)
    a = apply_measures(
        base,
        [
            HeatingReplacement(new_generator=HeatingGeneratorType.HEAT_PUMP_AIR_WATER),
            WallInsulation(),
        ],
    )
    b = apply_measures(
        base,
        [
            WallInsulation(),
            HeatingReplacement(new_generator=HeatingGeneratorType.HEAT_PUMP_AIR_WATER),
        ],
    )
    assert simulate(a).primary_energy_kwh_m2 == simulate(b).primary_energy_kwh_m2


def test_dhw_upgrade_to_heat_pump_water_heater() -> None:
    base = house_1970_oil_uninsulated()
    renovated = DHWUpgrade().apply(base)
    assert renovated.dhw_system.generator_type is DHWGeneratorType.HEAT_PUMP_WATER_HEATER
    before = simulate(base).final_energy_kwh_by_use["dhw"]
    after = simulate(renovated).final_energy_kwh_by_use["dhw"]
    assert after < before
