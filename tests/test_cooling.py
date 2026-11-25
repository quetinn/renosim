"""Tests for the conventional cooling chain (3CL §10, #16 brique 2).

Hand-computed reference (June, H1a, 100 m2 uninsulated house below):

- Nadeq: Shmoy = 100 -> Nmax = 0.025*100 = 2.5 -> Nadeq = 1.75 + 0.3*0.75 = 1.975
- Internal gains: (3.52*100 + 90*(132/168)*1.975) * Nref28(19 h) = 9341.6 Wh
- Solar aperture: 16.67 m2 * Sw 0.78 = 13.0026 m2; summer coefficient =
  0.5 * mean(C1_summer H1a = (1.0+1.0+0.598+0.955)/4 = 0.88825) / 0.6 (winter
  vertical mean) = 0.74021 -> Sse_fr = 9.6246 m2
- Solar gains: 1000 * 9.6246 * E_fr28(5.98) = 57 555.3 Wh -> gains = 66 896.9 Wh
- DH28 June H1a = 22.5 degC.h; Rbth = 66896.9 / (GV * 22.5)
- Medium inertia: Cin = 165000*100 J/K, t = Cin/(3600*GV) h, a = 1 + t/15
- fut = (1 - Rbth^-a) / (1 - Rbth^-(a+1))
- Bfr_June = gains/1000 + fut * GV * 22.5 / 1000    [(Tint-Text)*Nref = -DH28]
"""

import pytest

from renosim.envelope import envelope_heat_loss
from renosim.models import (
    AltitudeClass,
    Building,
    ClimateZone,
    ConstructionPeriod,
    CoolingPeriod,
    DHWGeneratorType,
    DHWSystem,
    EnergyCarrier,
    GlazingOrientation,
    HeatingGeneratorType,
    HeatingSystem,
    OpaqueEnvelopeElement,
    VentilationSystem,
    VentilationType,
    Window,
)
from renosim.needs import annual_needs, monthly_cooling_needs
from renosim.occupancy import CONVENTIONAL
from renosim.simulation import simulate
from renosim.systems import cooling_consumption, cooling_eer


def make_house(**overrides: object) -> Building:
    """100 m2 uninsulated 1948-1974 house (the F-G reference geometry)."""
    defaults: dict[str, object] = {
        "living_area_m2": 100.0,
        "construction_period": ConstructionPeriod.Y1948_1974,
        "climate_zone": ClimateZone.H1A,
        "altitude_class": AltitudeClass.LOW,
        "walls": (OpaqueEnvelopeElement(area_m2=83.33, u_value_w_per_m2k=2.0),),
        "roof": OpaqueEnvelopeElement(area_m2=100.0, u_value_w_per_m2k=2.5),
        "floor": OpaqueEnvelopeElement(
            area_m2=100.0, u_value_w_per_m2k=2.0, unheated_space_reduction_coefficient=0.183
        ),
        "windows": (Window(area_m2=16.67, u_value_w_per_m2k=5.8, solar_factor=0.78),),
        "heating_system": HeatingSystem(
            HeatingGeneratorType.STANDARD_BOILER, EnergyCarrier.FUEL_OIL, 30.0
        ),
        "dhw_system": DHWSystem(DHWGeneratorType.COUPLED_TO_HEATING_SYSTEM, EnergyCarrier.FUEL_OIL),
        "ventilation_system": VentilationSystem(VentilationType.NATURAL),
    }
    defaults.update(overrides)
    return Building(**defaults)  # type: ignore[arg-type]


class TestCoolingNeeds:
    def test_no_need_outside_the_cooling_season(self) -> None:
        needs = monthly_cooling_needs(make_house(), CONVENTIONAL)
        for month in (1, 2, 3, 4, 11, 12):
            assert needs[month] == 0.0

    def test_hand_computed_june_need(self) -> None:
        building = make_house()
        gv = envelope_heat_loss(building).gv_w_per_k
        gains_wh = 9341.6 + 57555.3  # internal + solar, see module docstring
        rbth = gains_wh / (gv * 22.5)
        a = 1.0 + 165000.0 * 100.0 / (3600.0 * gv) / 15.0
        fut = (1.0 - rbth**-a) / (1.0 - rbth ** -(a + 1.0))
        expected = gains_wh / 1000.0 + fut * gv * 22.5 / 1000.0
        needs = monthly_cooling_needs(building, CONVENTIONAL)
        assert needs[6] == pytest.approx(expected, rel=1e-3)
        # order of magnitude sanity: an uninsulated H1a house needs ~80 kWh in June
        assert 60.0 < needs[6] < 100.0

    def test_south_of_france_needs_much_more_cooling(self) -> None:
        north = annual_needs(make_house(), CONVENTIONAL).cooling_kwh
        south = annual_needs(make_house(climate_zone=ClimateZone.H3), CONVENTIONAL).cooling_kwh
        assert south > 4.0 * north

    def test_summer_orientation_ordering(self) -> None:
        # In summer, north glazing gains least; east/west slightly more than south.
        def bfr(orientation: GlazingOrientation) -> float:
            b = make_house(climate_zone=ClimateZone.H3, glazing_orientation=orientation)
            return annual_needs(b, CONVENTIONAL).cooling_kwh

        assert bfr(GlazingOrientation.NORTH) < bfr(GlazingOrientation.SOUTH)
        assert bfr(GlazingOrientation.SOUTH) < bfr(GlazingOrientation.EAST_WEST)

    def test_need_is_computed_even_without_air_conditioning(self) -> None:
        needs = annual_needs(make_house(climate_zone=ClimateZone.H3), CONVENTIONAL)
        assert needs.cooling_kwh > 0.0


class TestCoolingConsumption:
    def test_zero_without_declared_air_conditioner(self) -> None:
        building = make_house(climate_zone=ClimateZone.H3)
        assert cooling_consumption(building, 1000.0).final_energy_kwh == 0.0

    def test_cfr_formula_recent_split_h1(self) -> None:
        # H1/H2 from 2015: SEER 6.7 -> EER = 0.95*6.7 = 6.365; Cfr = 0.9*B/EER.
        building = make_house(
            has_air_conditioning=True, air_conditioning_period=CoolingPeriod.FROM_2015
        )
        assert cooling_eer(building) == pytest.approx(6.365)
        assert cooling_consumption(building, 1000.0).final_energy_kwh == pytest.approx(
            0.9 * 1000.0 / 6.365
        )

    def test_pre_2008_column_is_a_direct_eer(self) -> None:
        building = make_house(
            climate_zone=ClimateZone.H3,
            has_air_conditioning=True,
            air_conditioning_period=CoolingPeriod.BEFORE_2008,
        )
        assert cooling_eer(building) == pytest.approx(3.25)  # no 0.95 factor

    def test_unknown_period_uses_recent_bracket(self) -> None:
        building = make_house(climate_zone=ClimateZone.H3, has_air_conditioning=True)
        assert cooling_eer(building) == pytest.approx(0.95 * 7.5)

    def test_consumption_is_electric(self) -> None:
        building = make_house(has_air_conditioning=True)
        assert cooling_consumption(building, 500.0).energy_carrier is EnergyCarrier.ELECTRICITY


class TestSimulationIntegration:
    def test_label_and_ep_unchanged_without_air_conditioning(self) -> None:
        base = make_house(climate_zone=ClimateZone.H3)
        result = simulate(base)
        assert result.final_energy_kwh_by_use["cooling"] == 0.0
        assert result.needs.cooling_kwh > 0.0  # the need remains an indicator

    def test_air_conditioning_increases_primary_energy(self) -> None:
        base = make_house(climate_zone=ClimateZone.H3)
        with_ac = make_house(climate_zone=ClimateZone.H3, has_air_conditioning=True)
        r_base, r_ac = simulate(base), simulate(with_ac)
        assert r_ac.primary_energy_kwh_m2 > r_base.primary_energy_kwh_m2
        assert r_ac.co2_kg_m2 > r_base.co2_kg_m2
        assert r_ac.final_energy_kwh_by_use["cooling"] > 0.0

    def test_older_air_conditioner_consumes_more(self) -> None:
        recent = make_house(
            climate_zone=ClimateZone.H3,
            has_air_conditioning=True,
            air_conditioning_period=CoolingPeriod.FROM_2015,
        )
        old = make_house(
            climate_zone=ClimateZone.H3,
            has_air_conditioning=True,
            air_conditioning_period=CoolingPeriod.BEFORE_2008,
        )
        assert (
            simulate(old).final_energy_kwh_by_use["cooling"]
            > simulate(recent).final_energy_kwh_by_use["cooling"]
        )
