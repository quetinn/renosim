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
    added_r_from_insulation,
    apply_measures,
)
from tests.test_reference_cases import house_1970_oil_uninsulated


class TestAddedRFromInsulation:
    """R = thickness / lambda, lambda from tables/insulation_materials.json."""

    def test_glass_wool_28cm_gives_r7(self) -> None:
        # lambda = 0.040 -> R = 0.28 / 0.040 = 7.0
        assert added_r_from_insulation("glass_wool", 28.0) == pytest.approx(7.0)

    def test_polyurethane_12cm_gives_r4(self) -> None:
        # lambda = 0.030 -> R = 0.12 / 0.030 = 4.0
        assert added_r_from_insulation("polyurethane", 12.0) == pytest.approx(4.0)

    def test_eps_21cm_gives_r5(self) -> None:
        # lambda = 0.042 -> R = 0.21 / 0.042 = 5.0
        assert added_r_from_insulation("eps", 21.0) == pytest.approx(5.0)

    def test_unknown_material_uses_3cl_default_lambda(self) -> None:
        # 3CL convention: lambda = 0.04 when the insulant is not identified
        assert added_r_from_insulation("unknown", 20.0) == pytest.approx(5.0)

    def test_unlisted_material_rejected(self) -> None:
        with pytest.raises(ValueError, match="material"):
            added_r_from_insulation("asbestos", 10.0)

    def test_nonpositive_thickness_rejected(self) -> None:
        with pytest.raises(ValueError, match="thickness"):
            added_r_from_insulation("glass_wool", 0.0)


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


class TestSolarProtectionInstallation:
    """#16 brique 3: pure summer measure (volets/BSO)."""

    def test_lifts_the_insufficient_level(self) -> None:
        from dataclasses import replace

        from renosim.models import SolarProtectionLevel
        from renosim.renovation import SolarProtectionInstallation
        from renosim.summer_comfort import SummerComfortLevel, assess_summer_comfort

        exposed = replace(
            house_1970_oil_uninsulated(),
            roof_insulated=True,
            exterior_solar_protections=SolarProtectionLevel.NONE,
        )
        assert assess_summer_comfort(exposed).level is SummerComfortLevel.INSUFFICIENT
        after = SolarProtectionInstallation().apply(exposed)
        assert after.exterior_solar_protections is SolarProtectionLevel.FULL
        assert assess_summer_comfort(after).level is not SummerComfortLevel.INSUFFICIENT

    def test_no_effect_on_energy(self) -> None:
        from renosim.renovation import SolarProtectionInstallation

        before = house_1970_oil_uninsulated()
        after = SolarProtectionInstallation().apply(before)
        assert simulate(after).primary_energy_kwh_m2 == simulate(before).primary_energy_kwh_m2


class TestHeatingReplacementDHW:
    """A boiler-coupled DHW follows the new generator only if it can serve it."""

    def test_coupled_dhw_follows_a_hydraulic_generator(self) -> None:
        base = house_1970_oil_uninsulated()
        assert base.dhw_system.generator_type is DHWGeneratorType.COUPLED_TO_HEATING_SYSTEM
        after = HeatingReplacement(HeatingGeneratorType.CONDENSING_BOILER).apply(base)
        assert after.dhw_system.generator_type is DHWGeneratorType.COUPLED_TO_HEATING_SYSTEM
        assert after.dhw_system.energy_carrier is EnergyCarrier.NATURAL_GAS

    def test_pellet_stove_cannot_produce_dhw(self) -> None:
        # A stove has no hydraulic network: the coupled DHW must move to an
        # electric storage water heater instead of being "produced by the stove"
        # (audit 2026-11-25, §4.1).
        base = house_1970_oil_uninsulated()
        after = HeatingReplacement(HeatingGeneratorType.WOOD_PELLET_STOVE).apply(base)
        assert after.dhw_system.generator_type is DHWGeneratorType.ELECTRIC_STORAGE
        assert after.dhw_system.energy_carrier is EnergyCarrier.ELECTRICITY
        result = simulate(after)
        assert (
            result.final_energy_kwh_by_carrier.get(EnergyCarrier.ELECTRICITY, 0.0)
            > (result.final_energy_kwh_by_use["dhw"])
        )

    def test_explicit_dhw_upgrade_wins_whatever_the_order(self) -> None:
        base = house_1970_oil_uninsulated()
        stove = HeatingReplacement(HeatingGeneratorType.WOOD_PELLET_STOVE)
        bundles: list[list[RenovationMeasure]] = [[stove, DHWUpgrade()], [DHWUpgrade(), stove]]
        for bundle in bundles:
            after = apply_measures(base, bundle)
            assert after.dhw_system.generator_type is DHWGeneratorType.HEAT_PUMP_WATER_HEATER
