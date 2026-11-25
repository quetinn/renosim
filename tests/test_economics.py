"""Tests for renosim.economics — investment ranges, savings, simple payback.

Hand-computed cost reference (test_cost_range_hand_computed):
House walls 120 m2, roof 100 m2, windows 15 m2.
WallInsulation: 120 * [18, 238] = [2160, 28560] EUR
RoofInsulation: 100 * [17, 93] = [1700, 9300] EUR
WindowReplacement: 15 * [170, 1070] = [2550, 16050] EUR
HeatingReplacement PAC: [9000, 18000] EUR (lump sum)
Bundle total: low 2160+1700+2550+9000 = 15410 ; high 28560+9300+16050+18000 = 71910
(all in the source price years).

Indexation to the reference date (INSEE BT01, base 2010; audit §3.3):
  ONRE ranges (2019 prices): x 139.1 / 111.05 = 1.252589  (Sept. 2026 / 2019 mean)
  professional guides (2025 prices): x 139.1 / 133.01 = 1.045786 (Sept. 2026 / 2025 mean)
  -> walls [2705.59, 35773.94], roof [2129.40, 11649.08], windows [3194.10, 20104.05],
     PAC [9412.07, 18824.15]; bundle low 17441.17, high 86351.22
"""

import pytest

from renosim.economics import assess_scenario, measure_cost_range
from renosim.models import HeatingGeneratorType
from renosim.renovation import (
    HeatingReplacement,
    RenovationMeasure,
    RoofInsulation,
    WallInsulation,
    WindowReplacement,
)
from tests.test_reference_cases import house_1970_oil_uninsulated

#: BT01 indexation factors (see module docstring).
ONRE = 139.1 / 111.05
GUIDES = 139.1 / 133.01


def test_cost_range_hand_computed() -> None:
    base = house_1970_oil_uninsulated()
    low, high = measure_cost_range(base, WallInsulation())
    assert (low, high) == pytest.approx((2160.0 * ONRE, 28560.0 * ONRE))
    assert (low, high) == pytest.approx((2705.59, 35773.94), abs=0.01)
    low, high = measure_cost_range(base, RoofInsulation())
    assert (low, high) == pytest.approx((2129.40, 11649.08), abs=0.01)
    low, high = measure_cost_range(base, WindowReplacement())
    assert (low, high) == pytest.approx((3194.10, 20104.05), abs=0.01)
    low, high = measure_cost_range(
        base, HeatingReplacement(new_generator=HeatingGeneratorType.HEAT_PUMP_AIR_WATER)
    )
    assert (low, high) == pytest.approx((9000.0 * GUIDES, 18000.0 * GUIDES))
    assert (low, high) == pytest.approx((9412.07, 18824.15), abs=0.01)


def test_scenario_assessment_full_bundle() -> None:
    base = house_1970_oil_uninsulated()
    measures: list[RenovationMeasure] = [
        WallInsulation(),
        RoofInsulation(),
        WindowReplacement(),
        HeatingReplacement(new_generator=HeatingGeneratorType.HEAT_PUMP_AIR_WATER),
    ]
    assessment = assess_scenario(base, measures)

    assert assessment.investment_low_eur == pytest.approx(17441.17, abs=0.02)
    assert assessment.investment_high_eur == pytest.approx(86351.22, abs=0.02)
    assert assessment.annual_savings_eur > 0
    assert assessment.annual_co2_savings_kg > 0
    assert assessment.before.label in ("F", "G")
    assert assessment.after.label in ("B", "C", "D")
    # payback bounds ordered: cheaper investment pays back faster
    assert assessment.payback_years_low < assessment.payback_years_high
    assert assessment.payback_years_low > 0


def test_scenario_with_no_savings_has_infinite_payback() -> None:
    base = house_1970_oil_uninsulated()
    assessment = assess_scenario(base, [])  # empty bundle: nothing changes
    assert assessment.annual_savings_eur == pytest.approx(0.0)
    assert assessment.payback_years_low == float("inf")
    assert assessment.payback_years_high == float("inf")


def test_energy_savings_consistency() -> None:
    base = house_1970_oil_uninsulated()
    assessment = assess_scenario(base, [RoofInsulation()])
    manual = assessment.before.annual_cost_eur - assessment.after.annual_cost_eur
    assert assessment.annual_savings_eur == pytest.approx(manual)
