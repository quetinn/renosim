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

    def test_glazing_defaults_applied(self) -> None:
        b = building_from_json(base_building_json())
        assert b.windows[0].u_value_w_per_m2k == pytest.approx(4.8)
        assert b.windows[0].solar_factor == pytest.approx(0.56)

    def test_ground_floor_b_from_ue_table(self) -> None:
        b = building_from_json(base_building_json())
        ue = 0.36 + 0.02 * (2.0 - 1.43) / (3.33 - 1.43)
        assert b.floor.unheated_space_reduction_coefficient == pytest.approx(ue / 2.0)


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

    def test_measure_costs_cover_all_six_measures(self) -> None:
        costs = run(payload())["measure_costs"]
        assert set(costs) == {
            "wall_insulation",
            "roof_insulation",
            "window_replacement",
            "ventilation_upgrade",
            "heating_replacement",
            "dhw_upgrade",
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
