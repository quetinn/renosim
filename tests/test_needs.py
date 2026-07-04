"""Tests for renosim.needs — heating needs (degree-hours) and DHW needs.

Hand-computed DHW reference (test_dhw_needs_hand_computed):
House 100 m2, zone H1a, altitude low, conventional scenario.
Nadeq: Shmoy=100 >= 70 -> Nmax = 0.025*100 = 2.5 >= 1.75
       Nadeq = 1.75 + 0.3*(2.5-1.75) = 1.975
January: Tefs(H1a, low) = 7.8 degC, nj = 31
Becs_1 = 1.163 * 1.975 * 56 * (40-7.8) * 31 / 1000 = 128.39 kWh

Hand-computed heating reference (test_heating_needs_hand_computed):
GV = 994.83 W/K (see test_envelope), January H1a low: DH19 = 11712.4 degC.h,
E = 38.36 kWh/m2, Nref = 744 h.
Ai_1 = (3.52*100 + 90*(132/168)*1.975) * 744 = 365 719 Wh
Sse = 15 m2 * 0.56 * 0.5 = 4.2 m2 ; As_1 = 1000*4.2*38.36 = 161 112 Wh
X = (161112+365719) / (994.83*11712.4) = 0.045216
F = (X - X^2.9) / (1 - X^2.9) (medium inertia) ~= 0.045143
Bch_1 = 994.83 * 11712.4 * (1-0.045143) / 1000 = 11 126.1 kWh
"""

import pytest

from renosim.needs import annual_needs, monthly_dhw_needs, monthly_heating_needs
from renosim.occupancy import CONVENTIONAL, OccupancyScenario
from tests.test_envelope import _bare_house_kwargs
from tests.test_models import make_reference_building


def test_dhw_needs_hand_computed() -> None:
    building = make_reference_building()
    dhw = monthly_dhw_needs(building, CONVENTIONAL)
    assert dhw[1] == pytest.approx(128.39, rel=1e-3)
    # December counts only 24 occupied days
    assert dhw[12] < dhw[1]
    assert len(dhw) == 12


def test_heating_needs_hand_computed() -> None:
    building = make_reference_building(**_bare_house_kwargs())
    heating = monthly_heating_needs(building, CONVENTIONAL)
    assert heating[1] == pytest.approx(11126.1, rel=2e-3)
    # July-August: no conventional heating season in H1a low altitude
    assert heating[7] == 0.0
    assert heating[8] == 0.0


def test_annual_needs_sum_monthly() -> None:
    building = make_reference_building(**_bare_house_kwargs())
    needs = annual_needs(building, CONVENTIONAL)
    assert needs.heating_kwh == pytest.approx(
        sum(monthly_heating_needs(building, CONVENTIONAL).values())
    )
    assert needs.dhw_kwh == pytest.approx(sum(monthly_dhw_needs(building, CONVENTIONAL).values()))
    assert needs.heating_kwh > 0
    assert needs.dhw_kwh > 0


def test_higher_setpoint_increases_needs() -> None:
    building = make_reference_building(**_bare_house_kwargs())
    conv = annual_needs(building, CONVENTIONAL)
    warm = annual_needs(building, OccupancyScenario(heating_setpoint_c=21.0))
    cool = annual_needs(building, OccupancyScenario(heating_setpoint_c=17.0))
    assert warm.heating_kwh > conv.heating_kwh > cool.heating_kwh


def test_occupants_override_changes_dhw_only() -> None:
    building = make_reference_building(**_bare_house_kwargs())
    conv = annual_needs(building, CONVENTIONAL)
    crowded = annual_needs(building, OccupancyScenario(occupants_override=5.0))
    assert crowded.dhw_kwh > conv.dhw_kwh
    # more occupants -> more internal gains -> slightly lower heating needs
    assert crowded.heating_kwh <= conv.heating_kwh
