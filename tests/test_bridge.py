"""Tests for the JSON bridge consumed by the web app through Pyodide.

Geometry expectations are hand-computed from the M-1 reconstruction rules
(square footprint, 4 exposed facades, windows = Sh/6):

- 100 m2, 1 level, detached: footprint = 100, side = 10, perimeter = 40,
  windows = 100/6 = 16.667, walls = 40 * 2.5 * 1 - 16.667 = 83.333 m2.
- one shared wall: exposed perimeter = 30, walls = 75 - 16.667 = 58.333 m2.

Ground-floor b (M-7, Ue row 2S/P = 5): Upb = 2.0 interpolates between
(3.33, 0.38) and (1.43, 0.36): Ue = 0.36 + 0.02 * (2.0 - 1.43) / (3.33 - 1.43)
= 0.366; b = 0.366 / 2.0 = 0.183.
"""

import json
import math
from typing import Any

import pytest

from renosim import SCHEMA_VERSION, simulate
from renosim.bridge import building_from_json, parse_measures, run_simulation
from renosim.outputs import DEFAULT_REGULATION_VINTAGE


def base_building_json() -> dict[str, Any]:
    """~1970, 100 m2, uninsulated, old oil boiler, zone H1a — the F-G reference."""
    return {
        "living_area_m2": 100.0,
        "levels": 1,
        "construction_period": "1948_1974",
        "climate_zone": "H1a",
        "altitude_class": "low",
        "adjacency": "detached",
        "wall_insulation": {"state": "uninsulated"},
        "roof_insulation": {"state": "uninsulated"},
        "floor_insulation": {"state": "uninsulated"},
        "glazing": "single_glazing",
        "heating": {"generator": "standard_boiler", "carrier": "fuel_oil", "age_years": 30},
        "dhw": {"generator": "coupled_to_heating_system"},
        "ventilation": {"type": "natural"},
    }


def payload(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "building": base_building_json(),
        "occupancy": {"mode": "conventional"},
        "scenarios": [],
    }
    base.update(overrides)
    return base


def run(payload_dict: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = json.loads(run_simulation(json.dumps(payload_dict)))
    return result


class TestSchema:
    def test_rejects_unknown_schema_version(self) -> None:
        with pytest.raises(ValueError, match="schema_version"):
            run(payload(schema_version="99.0"))

    def test_output_carries_schema_and_engine_versions(self) -> None:
        out = run(payload())
        assert out["schema_version"] == SCHEMA_VERSION
        assert out["engine"]["name"] == "renosim"

    def test_default_vintage_is_the_one_in_force(self) -> None:
        # Electric house: omitting the vintage must equal the convention in
        # force today, and the output reports which one was applied.
        building = base_building_json()
        building["heating"] = {"generator": "electric_joule", "carrier": "electricity"}
        building["dhw"] = {"generator": "electric_storage"}
        out = run(payload(building=building))
        today = DEFAULT_REGULATION_VINTAGE
        explicit = run(payload(building=building, regulation_vintage=today))
        assert out["conventions"]["regulation_vintage"] == today
        assert (
            out["baseline"]["conventional"]["primary_energy_kwh_m2"]
            == explicit["baseline"]["conventional"]["primary_energy_kwh_m2"]
        )
        old = run(payload(building=building, regulation_vintage="dpe_2021"))
        assert old["conventions"]["electricity_primary_energy_factor"] == 2.3

    def test_output_reports_the_energy_price_convention(self) -> None:
        prices = run(payload())["conventions"]["energy_prices"]
        assert prices["date_in_force"] == "2024-07-01"
        assert "25 mars 2024" in prices["label"]
        costs = run(payload())["conventions"]["renovation_costs"]
        assert costs == {"index": "BT01", "reference_period": "2026-09"}


class TestGeometry:
    def test_detached_areas(self) -> None:
        b = building_from_json(base_building_json())
        assert sum(w.area_m2 for w in b.windows) == pytest.approx(100.0 / 6.0)
        assert sum(w.area_m2 for w in b.walls) == pytest.approx(40.0 * 2.5 - 100.0 / 6.0)
        assert b.roof.area_m2 == pytest.approx(100.0)
        assert b.floor.area_m2 == pytest.approx(100.0)

    def test_one_shared_wall_reduces_exposed_walls(self) -> None:
        data = base_building_json()
        data["adjacency"] = "one_shared_wall"
        b = building_from_json(data)
        assert sum(w.area_m2 for w in b.walls) == pytest.approx(30.0 * 2.5 - 100.0 / 6.0)

    def test_two_levels_halve_footprint(self) -> None:
        data = base_building_json()
        data["levels"] = 2
        b = building_from_json(data)
        # footprint = 50, side = sqrt(50), perimeter = 4*sqrt(50), 2 levels
        expected_walls = 4.0 * math.sqrt(50.0) * 2.5 * 2 - 100.0 / 6.0
        assert sum(w.area_m2 for w in b.walls) == pytest.approx(expected_walls)
        assert b.roof.area_m2 == pytest.approx(50.0)


class TestUResolution:
    def test_uninsulated_wall_uses_traditional_value(self) -> None:
        b = building_from_json(base_building_json())
        assert b.walls[0].u_value_w_per_m2k == pytest.approx(2.0)  # M-6
        assert b.roof.u_value_w_per_m2k == pytest.approx(2.5)
        assert b.floor.u_value_w_per_m2k == pytest.approx(2.0)

    def test_period_default_maps_pre_1975_to_75_77_row(self) -> None:
        data = base_building_json()
        data["wall_insulation"] = {"state": "period_default"}
        b = building_from_json(data)
        assert b.walls[0].u_value_w_per_m2k == pytest.approx(1.0)  # H1/others/1975_1977

    def test_renovated_uses_post_2013_row(self) -> None:
        data = base_building_json()
        data["wall_insulation"] = {"state": "renovated"}
        b = building_from_json(data)
        assert b.walls[0].u_value_w_per_m2k == pytest.approx(0.23)

    def test_known_r_composes_with_uninsulated_base(self) -> None:
        data = base_building_json()
        data["wall_insulation"] = {"state": "known_r", "r_value_m2k_per_w": 3.7}
        b = building_from_json(data)
        assert b.walls[0].u_value_w_per_m2k == pytest.approx(1.0 / (1.0 / 2.0 + 3.7))

    def test_known_insulation_material_and_thickness(self) -> None:
        # glass wool 20 cm: R = 0.20 / 0.040 = 5.0 -> U = 1/(1/2.0 + 5.0)
        data = base_building_json()
        data["wall_insulation"] = {"state": "known_r", "material": "glass_wool", "thickness_cm": 20}
        b = building_from_json(data)
        assert b.walls[0].u_value_w_per_m2k == pytest.approx(1.0 / (1.0 / 2.0 + 5.0))

    def test_known_insulation_unlisted_material_rejected(self) -> None:
        data = base_building_json()
        data["roof_insulation"] = {"state": "known_r", "material": "straw", "thickness_cm": 30}
        with pytest.raises(ValueError, match="material"):
            building_from_json(data)

    def test_glazing_defaults_applied(self) -> None:
        b = building_from_json(base_building_json())
        assert b.windows[0].u_value_w_per_m2k == pytest.approx(4.8)
        assert b.windows[0].solar_factor == pytest.approx(0.56)

    def test_ground_floor_b_from_ue_table(self) -> None:
        b = building_from_json(base_building_json())
        ue = 0.36 + 0.02 * (2.0 - 1.43) / (3.33 - 1.43)
        assert b.floor.unheated_space_reduction_coefficient == pytest.approx(ue / 2.0)


class TestFloorType:
    def test_unknown_and_vide_sanitaire_share_the_m7_table(self) -> None:
        vs = base_building_json()
        vs["floor_type"] = "vide_sanitaire"
        default = building_from_json(base_building_json())
        explicit = building_from_json(vs)
        assert explicit.floor.unheated_space_reduction_coefficient == pytest.approx(
            default.floor.unheated_space_reduction_coefficient
        )

    def test_terre_plein_pre_2001_hand_computed(self) -> None:
        # Upb = 2.0, table p.19 avant 2001: interpolate (3.4, 0.6)-(1.5, 0.46):
        # Ue = 0.46 + 0.14*(2.0-1.5)/(3.4-1.5) = 0.49684 -> b = 0.24842
        data = base_building_json()
        data["floor_type"] = "terre_plein"
        b = building_from_json(data)
        expected_ue = 0.46 + 0.14 * (2.0 - 1.5) / (3.4 - 1.5)
        assert b.floor.unheated_space_reduction_coefficient == pytest.approx(expected_ue / 2.0)

    def test_terre_plein_post_2001_uses_recent_table(self) -> None:
        # Upb = 2.0, table p.19 à partir de 2001: (3.4, 0.58)-(1.5, 0.5):
        # Ue = 0.5 + 0.08*(2.0-1.5)/(3.4-1.5) = 0.52105 -> b = 0.26053
        data = base_building_json()
        data["construction_period"] = "2006_2012"
        data["floor_type"] = "terre_plein"
        b = building_from_json(data)
        expected_ue = 0.5 + 0.08 * (2.0 - 1.5) / (3.4 - 1.5)
        assert b.floor.unheated_space_reduction_coefficient == pytest.approx(expected_ue / 2.0)

    def test_unheated_space_flat_b(self) -> None:
        # Garage/cellier: b = 0.95 (table §3.1 p.10), Upb kept as-is.
        data = base_building_json()
        data["floor_type"] = "local_non_chauffe"
        b = building_from_json(data)
        assert b.floor.unheated_space_reduction_coefficient == pytest.approx(0.95)
        assert b.floor.u_value_w_per_m2k == pytest.approx(2.0)

    def test_unknown_floor_type_rejected(self) -> None:
        data = base_building_json()
        data["floor_type"] = "piscine"
        with pytest.raises(ValueError, match="floor_type"):
            building_from_json(data)


class TestSolarInputs:
    def test_orientation_and_shading_passthrough(self) -> None:
        data = base_building_json()
        data["glazing_orientation"] = "south"
        data["solar_shading"] = "partial"
        b = building_from_json(data)
        assert b.glazing_orientation.value == "south"
        assert b.solar_shading.value == "partial"

    def test_defaults_are_neutral(self) -> None:
        b = building_from_json(base_building_json())
        assert b.glazing_orientation.value == "unknown"
        assert b.solar_shading.value == "clear_or_unknown"

    def test_south_facing_lowers_conventional_consumption(self) -> None:
        south = base_building_json()
        south["glazing_orientation"] = "south"
        base = simulate(building_from_json(base_building_json()))
        oriented = simulate(building_from_json(south))
        assert oriented.primary_energy_kwh_m2 < base.primary_energy_kwh_m2


class TestInertia:
    def test_default_is_unknown(self) -> None:
        b = building_from_json(base_building_json())
        assert b.inertia.value == "unknown"

    def test_passthrough(self) -> None:
        data = base_building_json()
        data["inertia"] = "heavy"
        assert building_from_json(data).inertia.value == "heavy"

    def test_inertia_changes_the_conventional_result(self) -> None:
        # Heavy inertia has two opposite official effects: a higher
        # utilization-factor exponent (lower needs, §6.1) and a higher
        # intermittence base I0 (higher consumption, §8) — the net direction
        # depends on the building, so only a difference is asserted here (the
        # two effects are pinned separately in test_needs and test_systems).
        heavy = base_building_json()
        heavy["inertia"] = "heavy"
        light = base_building_json()
        light["inertia"] = "light"
        heavy_res = simulate(building_from_json(heavy))
        light_res = simulate(building_from_json(light))
        assert heavy_res.primary_energy_kwh_m2 != pytest.approx(light_res.primary_energy_kwh_m2)

    def test_unknown_inertia_value_rejected(self) -> None:
        data = base_building_json()
        data["inertia"] = "granite"
        with pytest.raises(ValueError, match="granite"):
            building_from_json(data)


class TestLabelTargets:
    _CLASSES = "ABCDEFG"

    def test_null_when_not_requested(self) -> None:
        assert run(payload())["label_targets"] is None

    def test_targets_beat_the_baseline_label(self) -> None:
        out = run(payload(label_targets={}))
        baseline_label = out["baseline"]["conventional"]["label"]
        targets = out["label_targets"]
        assert targets  # the F-G house can always gain at least one class
        for target, entry in targets.items():
            assert self._CLASSES.index(target) < self._CLASSES.index(baseline_label)
            # The winning combination reaches at least the target class.
            assert self._CLASSES.index(entry["after_label"]) <= self._CLASSES.index(target)
            assert entry["measures"]
            assert 0 < entry["investment_low_eur"] <= entry["investment_high_eur"]

    def test_stricter_target_never_cheaper(self) -> None:
        # Any combination reaching class X also satisfies every looser target,
        # so the best mid-range investment must grow as the target tightens.
        targets = run(payload(label_targets={}))["label_targets"]
        ordered = sorted(targets, key=self._CLASSES.index)  # best class first
        mids = [
            (targets[t]["investment_low_eur"] + targets[t]["investment_high_eur"]) / 2
            for t in ordered
        ]
        assert mids == sorted(mids, reverse=True)

    def test_measures_override_restricts_the_search(self) -> None:
        out = run(payload(label_targets={"measures": [{"type": "roof_insulation"}]}))
        for entry in out["label_targets"].values():
            assert [m["type"] for m in entry["measures"]] == ["roof_insulation"]

    def test_full_override_replaces_reconstruction(self) -> None:
        data = base_building_json()
        data["geometry"] = {
            "wall_area_m2": 120.0,
            "window_area_m2": 20.0,
            "roof_area_m2": 90.0,
            "floor_area_m2": 95.0,
        }
        b = building_from_json(data)
        assert sum(w.area_m2 for w in b.walls) == pytest.approx(120.0)
        assert sum(w.area_m2 for w in b.windows) == pytest.approx(20.0)
        assert b.roof.area_m2 == pytest.approx(90.0)
        assert b.floor.area_m2 == pytest.approx(95.0)

    def test_partial_override_keeps_m1_for_the_rest(self) -> None:
        data = base_building_json()
        data["geometry"] = {"window_area_m2": 25.0}
        b = building_from_json(data)
        assert sum(w.area_m2 for w in b.windows) == pytest.approx(25.0)
        # M-1 wall reconstruction now subtracts the overridden window area.
        assert sum(w.area_m2 for w in b.walls) == pytest.approx(40.0 * 2.5 - 25.0)
        assert b.roof.area_m2 == pytest.approx(100.0)

    def test_ceiling_height_override(self) -> None:
        data = base_building_json()
        data["geometry"] = {"ceiling_height_m": 3.0}
        b = building_from_json(data)
        assert sum(w.area_m2 for w in b.walls) == pytest.approx(40.0 * 3.0 - 100.0 / 6.0)

    def test_nonpositive_override_rejected(self) -> None:
        data = base_building_json()
        data["geometry"] = {"wall_area_m2": 0.0}
        with pytest.raises(ValueError, match="wall_area_m2"):
            building_from_json(data)


class TestBaseline:
    def test_matches_direct_engine_call(self) -> None:
        out = run(payload())
        direct = simulate(building_from_json(base_building_json()))
        conv = out["baseline"]["conventional"]
        assert conv["primary_energy_kwh_m2"] == pytest.approx(direct.primary_energy_kwh_m2)
        assert conv["co2_kg_m2"] == pytest.approx(direct.co2_kg_m2)
        assert conv["label"] == direct.label
        assert conv["annual_cost_eur"] == pytest.approx(direct.annual_cost_eur)

    def test_reference_house_lands_f_or_g(self) -> None:
        out = run(payload())
        assert out["baseline"]["conventional"]["label"] in ("F", "G")

    def test_envelope_breakdown_sums_to_total(self) -> None:
        env = run(payload())["baseline"]["conventional"]["envelope"]
        parts = (
            env["walls_w_per_k"]
            + env["roof_w_per_k"]
            + env["floor_w_per_k"]
            + env["windows_w_per_k"]
            + env["thermal_bridges_w_per_k"]
            + env["ventilation_w_per_k"]
            + env["infiltration_w_per_k"]
        )
        assert env["total_w_per_k"] == pytest.approx(parts)

    def test_personalized_run_present_without_label(self) -> None:
        out = run(
            payload(occupancy={"mode": "personalized", "heating_setpoint_c": 21, "occupants": 5})
        )
        perso = out["baseline"]["personalized"]
        assert perso is not None
        assert perso["label"] is None  # the DPE label must stay conventional
        conv = out["baseline"]["conventional"]
        assert conv["label"] is not None
        assert perso["final_energy_kwh_m2"] > conv["final_energy_kwh_m2"]  # 21 degC > 19 degC

    def test_personalized_price_override(self) -> None:
        out = run(
            payload(
                occupancy={
                    "mode": "personalized",
                    "energy_prices_eur_per_kwh": {"fuel_oil": 0.20, "electricity": 0.25},
                }
            )
        )
        perso = out["baseline"]["personalized"]
        by_carrier = perso["final_energy_kwh_by_carrier"]
        expected = by_carrier["fuel_oil"] * 0.20 + by_carrier["electricity"] * 0.25
        assert perso["annual_cost_eur"] == pytest.approx(expected)
        # The conventional cost must stay on the conventional tariffs.
        conv = out["baseline"]["conventional"]
        assert conv["annual_cost_eur"] != pytest.approx(expected)


class TestScenarios:
    def test_roof_insulation_improves_and_prices(self) -> None:
        out = run(
            payload(
                scenarios=[
                    {
                        "id": "combles",
                        "measures": [{"type": "roof_insulation", "added_r_m2k_per_w": 7.0}],
                    }
                ]
            )
        )
        sc = out["scenarios"][0]
        assert sc["id"] == "combles"
        conv = sc["conventional"]
        assert (
            conv["after"]["primary_energy_kwh_m2"]
            < (out["baseline"]["conventional"]["primary_energy_kwh_m2"])
        )
        assert 0 < conv["investment_low_eur"] < conv["investment_high_eur"]
        assert conv["annual_savings_eur"] > 0
        assert conv["payback_years_low"] is not None
        assert conv["payback_years_low"] <= conv["payback_years_high"]

    def test_full_bundle_reaches_c_or_d(self) -> None:
        measures = [
            {"type": "wall_insulation"},
            {"type": "roof_insulation"},
            {"type": "window_replacement"},
            {"type": "ventilation_upgrade"},
            {"type": "heating_replacement", "new_generator": "heat_pump_air_water"},
            {"type": "dhw_upgrade"},
        ]
        out = run(payload(scenarios=[{"id": "global", "measures": measures}]))
        after = out["scenarios"][0]["conventional"]["after"]
        assert after["label"] in ("B", "C", "D")

    def test_unknown_measure_type_rejected(self) -> None:
        with pytest.raises(ValueError, match="measure"):
            parse_measures([{"type": "solar_panels"}])

    def test_insulation_measure_from_material_and_thickness(self) -> None:
        # polyurethane 21 cm: R = 0.21 / 0.030 = 7.0 — same as an explicit R=7
        (from_material,) = parse_measures(
            [{"type": "roof_insulation", "material": "polyurethane", "thickness_cm": 21}]
        )
        (from_r,) = parse_measures([{"type": "roof_insulation", "added_r_m2k_per_w": 7.0}])
        b = building_from_json(base_building_json())
        assert from_material.apply(b).roof.u_value_w_per_m2k == pytest.approx(
            from_r.apply(b).roof.u_value_w_per_m2k
        )

    def test_insulation_measure_unlisted_material_rejected(self) -> None:
        with pytest.raises(ValueError, match="material"):
            parse_measures([{"type": "wall_insulation", "material": "straw", "thickness_cm": 10}])

    def test_measure_previews_cover_all_measures(self) -> None:
        previews = run(payload())["measure_previews"]
        assert set(previews) == {
            "wall_insulation",
            "roof_insulation",
            "window_replacement",
            "ventilation_upgrade",
            "heating_replacement",
            "dhw_upgrade",
            "solar_protection_installation",
        }
        for p in previews.values():
            assert "annual_savings_eur" in p
            assert "annual_co2_savings_kg" in p
            assert "after_label" in p
            # payback is null when savings are not positive, else low <= high
            if p["payback_years_low"] is not None:
                assert p["payback_years_low"] <= p["payback_years_high"]

    def test_measure_preview_matches_single_scenario_assessment(self) -> None:
        # A preview must equal the same measure run as a standalone scenario.
        out = run(
            payload(
                scenarios=[{"id": "roof_insulation", "measures": [{"type": "roof_insulation"}]}]
            )
        )
        preview = out["measure_previews"]["roof_insulation"]
        scenario = out["scenarios"][0]["conventional"]
        assert preview["annual_savings_eur"] == pytest.approx(scenario["annual_savings_eur"])
        assert preview["annual_co2_savings_kg"] == pytest.approx(scenario["annual_co2_savings_kg"])
        assert preview["after_label"] == scenario["after"]["label"]

    def test_measure_costs_cover_all_measures(self) -> None:
        costs = run(payload())["measure_costs"]
        assert set(costs) == {
            "wall_insulation",
            "roof_insulation",
            "window_replacement",
            "ventilation_upgrade",
            "heating_replacement",
            "dhw_upgrade",
            "solar_protection_installation",
        }
        assert all(0 < c["low_eur"] <= c["high_eur"] for c in costs.values())

    def test_bundles_exposed_with_serialized_measures(self) -> None:
        bundles = run(payload())["bundles"]
        assert set(bundles) == {"enveloppe_d_abord", "sortie_du_fioul", "renovation_globale"}
        assert len(bundles["renovation_globale"]) == 6
        assert all("type" in m for m in bundles["renovation_globale"])

    def test_personalized_scenario_assessment_present(self) -> None:
        out = run(
            payload(
                occupancy={"mode": "personalized", "heating_setpoint_c": 20},
                scenarios=[{"id": "s", "measures": [{"type": "roof_insulation"}]}],
            )
        )
        sc = out["scenarios"][0]
        assert sc["personalized"] is not None
        assert sc["personalized"]["after"]["label"] is None
        assert sc["conventional"]["after"]["label"] is not None


class TestApartment:
    """Apartment support (#15, D-18). Hand-computed geometry for Sh = 60 m2,
    hsp 2.5: full perimeter = 4*sqrt(60) = 30.98 m; through flat exposes 50 %
    -> walls = (15.49*2.5 - 10) * 1.85 = 53.14 m2 (windows = 60/6 = 10, wall
    area scaled by the calibrated wall_area_factor); non-through exposes 25 %
    -> (7.746*2.5 - 10) * 1.85 = 17.33 m2 + one circulation wall 7.746*2.5 =
    19.36 m2 (unscaled) at the official b = 0.35."""

    @staticmethod
    def _apartment_json(**apartment: object) -> dict[str, Any]:
        data = base_building_json()
        data["living_area_m2"] = 60.0
        data["dwelling_type"] = "apartment"
        data["apartment"] = apartment
        return data

    def test_through_intermediate_geometry(self) -> None:
        b = building_from_json(self._apartment_json(position="intermediate", traversant=True))
        assert len(b.walls) == 1
        assert b.walls[0].area_m2 == pytest.approx((15.49 * 2.5 - 10.0) * 1.85, rel=1e-3)
        assert b.roof.unheated_space_reduction_coefficient == 0.0
        assert b.floor.unheated_space_reduction_coefficient == 0.0
        assert b.single_exposed_facade is False

    def test_non_through_adds_circulation_wall(self) -> None:
        b = building_from_json(self._apartment_json(position="intermediate", traversant=False))
        assert len(b.walls) == 2
        exposed, circulation = b.walls
        assert exposed.area_m2 == pytest.approx((7.746 * 2.5 - 10.0) * 1.85, rel=1e-2)
        assert circulation.area_m2 == pytest.approx(7.746 * 2.5, rel=1e-3)
        assert circulation.unheated_space_reduction_coefficient == pytest.approx(0.35)
        assert b.single_exposed_facade is True

    def test_top_floor_exposes_roof(self) -> None:
        b = building_from_json(self._apartment_json(position="top"))
        assert b.roof.unheated_space_reduction_coefficient == 1.0
        assert b.floor.unheated_space_reduction_coefficient == 0.0

    def test_ground_floor_uses_house_floor_treatment(self) -> None:
        flat = building_from_json(self._apartment_json(position="ground"))
        house = building_from_json(base_building_json())
        assert flat.floor.unheated_space_reduction_coefficient == pytest.approx(
            house.floor.unheated_space_reduction_coefficient
        )

    def test_unknown_position_uses_calibrated_expected_b(self) -> None:
        # Calibrated on the apartment campaign (apartment_reconstruction table):
        # unknown position -> expected-value ceiling/floor adjacency.
        unknown = building_from_json(self._apartment_json())
        assert unknown.roof.unheated_space_reduction_coefficient == pytest.approx(0.45)
        assert unknown.floor.unheated_space_reduction_coefficient == pytest.approx(0.1)

    def test_invalid_position_rejected(self) -> None:
        with pytest.raises(ValueError, match="position"):
            building_from_json(self._apartment_json(position="penthouse"))

    def test_intermediate_apartment_beats_equivalent_house(self) -> None:
        # Party walls/ceilings at b = 0: much less envelope -> better label
        # or at least strictly lower conventional consumption.
        flat = simulate(building_from_json(self._apartment_json(position="intermediate")))
        house_data = base_building_json()
        house_data["living_area_m2"] = 60.0
        house = simulate(building_from_json(house_data))
        assert flat.primary_energy_kwh_m2 < house.primary_energy_kwh_m2

    def test_apartment_runs_through_the_bridge(self) -> None:
        p = payload(building=self._apartment_json(position="top", traversant=False))
        out = run(p)
        assert out["baseline"]["conventional"]["label"] in list("ABCDEFG")


class TestSummerComfort:
    """#16 brique 1: summer block parsing and indicator outputs."""

    def test_defaults_unknown_protections_and_no_fans(self) -> None:
        b = building_from_json(base_building_json())
        assert b.exterior_solar_protections.value == "unknown"
        assert b.has_fixed_air_circulators is False
        assert b.has_air_conditioning is False
        assert b.through_dwelling is None  # house -> assumed through (D-19)

    def test_roof_insulated_follows_declared_winter_state(self) -> None:
        data = base_building_json()
        assert building_from_json(data).roof_insulated is False  # "uninsulated"
        data["roof_insulation"] = {"state": "period_default"}
        assert building_from_json(data).roof_insulated is None
        data["roof_insulation"] = {"state": "renovated"}
        assert building_from_json(data).roof_insulated is True

    def test_summer_block_is_parsed(self) -> None:
        data = base_building_json()
        data["summer"] = {
            "solar_protections": "partial",
            "fixed_air_circulators": True,
            "air_conditioning": True,
        }
        b = building_from_json(data)
        assert b.exterior_solar_protections.value == "partial"
        assert b.has_fixed_air_circulators is True
        assert b.has_air_conditioning is True

    def test_output_carries_summer_comfort_block(self) -> None:
        # 1948-1974 house, uninsulated roof -> insufficient by both criteria.
        out = run(payload())
        sc = out["summer_comfort"]
        assert sc["level"] == "insufficient"
        assert sc["criteria"]["roof_insulated"] is False
        assert sc["air_conditioning"] is False

    def test_roof_insulation_scenario_improves_summer_level(self) -> None:
        data = base_building_json()
        data["summer"] = {"solar_protections": "full"}
        p = payload(
            building=data,
            scenarios=[{"id": "roof", "measures": [{"type": "roof_insulation"}]}],
        )
        out = run(p)
        assert out["summer_comfort"]["level"] == "insufficient"
        after = out["scenarios"][0]["summer_comfort_after"]
        assert after["level"] == "medium"
        assert after["criteria"]["roof_insulated"] is True

    def test_measure_previews_carry_summer_level(self) -> None:
        out = run(payload())
        previews = out["measure_previews"]
        assert previews["roof_insulation"]["summer_comfort_level_after"] in (
            "insufficient",
            "medium",
            "good",
        )
        # Wall insulation does not touch the summer criteria of this house.
        assert previews["wall_insulation"]["summer_comfort_level_after"] == "insufficient"


class TestCooling:
    """#16 brique 2: air conditioning in the summer block and cooling outputs."""

    def test_cooling_need_reported_without_ac(self) -> None:
        data = base_building_json()
        data["climate_zone"] = "H3"
        out = run(payload(building=data))
        baseline = out["baseline"]["conventional"]
        assert baseline["needs"]["cooling_kwh"] > 0.0
        assert baseline["final_energy_kwh_by_use"]["cooling"] == 0.0
        assert out["summer_comfort"]["cooling_need_kwh_m2"] > 0.0

    def test_declared_ac_adds_cooling_consumption_and_ep(self) -> None:
        data = base_building_json()
        data["climate_zone"] = "H3"
        without = run(payload(building=data))
        data["summer"] = {"air_conditioning": True, "air_conditioning_period": "from_2015"}
        with_ac = run(payload(building=data))
        assert with_ac["baseline"]["conventional"]["final_energy_kwh_by_use"]["cooling"] > 0.0
        assert (
            with_ac["baseline"]["conventional"]["primary_energy_kwh_m2"]
            > without["baseline"]["conventional"]["primary_energy_kwh_m2"]
        )

    def test_ac_period_parsed(self) -> None:
        data = base_building_json()
        data["summer"] = {"air_conditioning": True, "air_conditioning_period": "before_2008"}
        b = building_from_json(data)
        assert b.has_air_conditioning is True
        assert b.air_conditioning_period.value == "before_2008"


def test_declared_ceiling_height_reaches_the_building() -> None:
    # Audit 2026-11-25 §4.10: the geometry override is no longer limited to
    # the surface reconstruction; unset keeps the conventional height.
    data = base_building_json()
    assert building_from_json(data).ceiling_height_m is None
    data["geometry"] = {"ceiling_height_m": 3.0}
    assert building_from_json(data).ceiling_height_m == 3.0


class TestHeatPumpSizing:
    """Design heat load and heat-pump check exposed to the app (audit §4.4)."""

    def test_baseline_design_load_follows_pnc_formula(self) -> None:
        out = run(payload())
        gv = out["baseline"]["conventional"]["envelope"]["total_w_per_k"]
        # H1a, altitude < 400 m: Tbase = -9.5 degC -> Pnc = GV * 29.5 / 1000.
        assert out["baseline"]["design_heat_load_kw"] == pytest.approx(gv * 29.5 / 1000)

    def test_sizing_only_for_a_new_heat_pump(self) -> None:
        out = run(
            payload(
                scenarios=[
                    {"id": "hp", "measures": [{"type": "heating_replacement"}]},
                    {"id": "walls", "measures": [{"type": "wall_insulation"}]},
                ]
            )
        )
        hp, walls = out["scenarios"]
        sizing = hp["heat_pump_sizing"]
        assert sizing["design_heat_load_kw"] == pytest.approx(
            out["baseline"]["design_heat_load_kw"]
        )
        assert (sizing["reference_power_low_kw"], sizing["reference_power_high_kw"]) == (10, 12)
        assert sizing["above_reference"] is True  # uninsulated 1970 house
        assert walls["heat_pump_sizing"] is None
        previews = out["measure_previews"]
        assert previews["heating_replacement"]["heat_pump_sizing"]["above_reference"] is True
        assert previews["roof_insulation"]["heat_pump_sizing"] is None


class TestHeatingBackup:
    """Wood stove/insert back-up from the form (3CL §9.3)."""

    def test_backup_parsed_with_its_carrier(self) -> None:
        data = base_building_json()
        data["heating_backup"] = {"generator": "wood_log_stove"}
        building = building_from_json(data)
        assert building.heating_backup is not None
        assert building.heating_backup.energy_carrier.value == "wood_logs"
        assert building.heating_backup.generator_age_years is None

    def test_backup_adds_wood_to_the_carriers(self) -> None:
        data = base_building_json()
        data["heating_backup"] = {"generator": "wood_pellet_stove", "age_years": 3}
        out = run(payload(building=data))
        carriers = out["baseline"]["conventional"]["final_energy_kwh_by_carrier"]
        assert carriers["wood_pellets"] > 0
        assert carriers["fuel_oil"] > 0

    def test_non_stove_backup_rejected(self) -> None:
        data = base_building_json()
        data["heating_backup"] = {"generator": "condensing_boiler"}
        with pytest.raises(ValueError, match="heating_backup"):
            building_from_json(data)


class TestInertiaElements:
    """Inertia from three yes/no questions (3CL §7.4) instead of a declared class."""

    def test_elements_override_the_declared_class(self) -> None:
        data = base_building_json()
        data["inertia"] = "light"
        data["inertia_elements"] = {
            "heavy_floor": True,
            "heavy_ceiling": False,
            "heavy_walls": True,
        }
        assert building_from_json(data).inertia.value == "heavy"

    def test_unknown_elements_give_medium(self) -> None:
        data = base_building_json()
        data["inertia_elements"] = {"heavy_floor": None, "heavy_ceiling": None, "heavy_walls": None}
        assert building_from_json(data).inertia.value == "medium"
