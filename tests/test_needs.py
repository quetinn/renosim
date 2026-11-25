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

from dataclasses import replace

import pytest

from renosim.models import GlazingOrientation, InertiaClass, SolarShading
from renosim.needs import (
    annual_needs,
    monthly_dhw_needs,
    monthly_heating_needs,
    solar_orientation_modifier,
    solar_shading_factor,
)
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


def test_inertia_class_orders_heating_needs() -> None:
    # Heavier inertia -> higher exponent (3.6 > 2.9 > 2.5) -> better use of the
    # free gains -> lower heating needs.
    base = make_reference_building(**_bare_house_kwargs())
    needs_by_class = {
        cls: annual_needs(replace(base, inertia=cls), CONVENTIONAL).heating_kwh
        for cls in (InertiaClass.LIGHT, InertiaClass.MEDIUM, InertiaClass.HEAVY)
    }
    assert (
        needs_by_class[InertiaClass.HEAVY]
        < needs_by_class[InertiaClass.MEDIUM]
        < needs_by_class[InertiaClass.LIGHT]
    )


def test_unknown_inertia_behaves_as_medium() -> None:
    base = make_reference_building(**_bare_house_kwargs())
    assert base.inertia is InertiaClass.UNKNOWN
    assert annual_needs(base, CONVENTIONAL).heating_kwh == pytest.approx(
        annual_needs(replace(base, inertia=InertiaClass.MEDIUM), CONVENTIONAL).heating_kwh
    )


def test_higher_setpoint_increases_needs() -> None:
    building = make_reference_building(**_bare_house_kwargs())
    conv = annual_needs(building, CONVENTIONAL)
    warm = annual_needs(building, OccupancyScenario(heating_setpoint_c=21.0))
    cool = annual_needs(building, OccupancyScenario(heating_setpoint_c=17.0))
    assert warm.heating_kwh > conv.heating_kwh > cool.heating_kwh


class TestSolarOrientationAndShading:
    """Orientation modifier = C1_orient / mean of the 4 orientations (§18.5 ratios).

    Hand-computed for H1a (heating-season VERTICAL C1 averages, >= 75 deg
    column — the table initially averaged the tilted column by mistake, see
    notes_correction in solar_orientation.json):
    south 1.0, west 0.521, north 0.347, east 0.530 -> mean = 0.5995.
    south modifier = 1.0/0.5995 = 1.6681 ; north = 0.347/0.5995 = 0.5788 ;
    east_west = ((0.521+0.530)/2)/0.5995 = 0.8765.
    """

    def test_modifier_hand_computed_h1a(self) -> None:
        b = make_reference_building()  # zone H1a
        south = replace(b, glazing_orientation=GlazingOrientation.SOUTH)
        north = replace(b, glazing_orientation=GlazingOrientation.NORTH)
        east_west = replace(b, glazing_orientation=GlazingOrientation.EAST_WEST)
        assert solar_orientation_modifier(south) == pytest.approx(1.0 / 0.5995, rel=1e-4)
        assert solar_orientation_modifier(north) == pytest.approx(0.347 / 0.5995, rel=1e-4)
        assert solar_orientation_modifier(east_west) == pytest.approx(0.8765, rel=1e-3)

    def test_unknown_orientation_is_neutral(self) -> None:
        # Calibration-preserving: the default journey reproduces the D-06 coefficient.
        assert solar_orientation_modifier(make_reference_building()) == 1.0

    def test_shading_factors_from_fe2_table(self) -> None:
        b = make_reference_building()
        assert solar_shading_factor(b) == 1.0  # clear_or_unknown
        assert solar_shading_factor(replace(b, solar_shading=SolarShading.PARTIAL)) == 0.8
        assert solar_shading_factor(replace(b, solar_shading=SolarShading.HEAVY)) == 0.4

    def test_orientation_and_shading_order_heating_needs(self) -> None:
        b = make_reference_building(**_bare_house_kwargs())
        south = annual_needs(replace(b, glazing_orientation=GlazingOrientation.SOUTH), CONVENTIONAL)
        unknown = annual_needs(b, CONVENTIONAL)
        north = annual_needs(replace(b, glazing_orientation=GlazingOrientation.NORTH), CONVENTIONAL)
        heavy = annual_needs(replace(b, solar_shading=SolarShading.HEAVY), CONVENTIONAL)
        assert south.heating_kwh < unknown.heating_kwh < north.heating_kwh
        assert heavy.heating_kwh > unknown.heating_kwh
        # DHW is unaffected by solar inputs
        assert south.dhw_kwh == pytest.approx(unknown.dhw_kwh)


def test_occupants_override_changes_dhw_only() -> None:
    building = make_reference_building(**_bare_house_kwargs())
    conv = annual_needs(building, CONVENTIONAL)
    crowded = annual_needs(building, OccupancyScenario(occupants_override=5.0))
    assert crowded.dhw_kwh > conv.dhw_kwh
    # more occupants -> more internal gains -> slightly lower heating needs
    assert crowded.heating_kwh <= conv.heating_kwh


def test_nadeq_apartment_thresholds() -> None:
    # §11.1 logements collectifs: Sh=60 -> Nmax = 0.035*60 = 2.1 >= 1.75
    # -> Nadeq = 1.75 + 0.3*(2.1-1.75) = 1.855 ; house 60 m2 -> 1.5625.
    from renosim.models import DwellingType
    from renosim.occupancy import equivalent_adults

    assert equivalent_adults(60.0, CONVENTIONAL, DwellingType.APARTMENT) == pytest.approx(1.855)
    assert equivalent_adults(60.0, CONVENTIONAL, DwellingType.HOUSE) == pytest.approx(1.5625)
    # Below 10 m2: Nmax = 1
    assert equivalent_adults(9.0, CONVENTIONAL, DwellingType.APARTMENT) == pytest.approx(1.0)
