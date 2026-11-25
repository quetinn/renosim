"""Tests for renosim.systems — needs -> final energy per use and carrier.

Hand-computed anchors:

Heating with an old oil boiler (standard formulas, Pn = 24 kW):
  log10(24) = 1.3802
  Rpn = (84 + 2*1.3802)/100 = 0.86760 ; Rpint = (80 + 3*1.3802)/100 = 0.84141
  Rg_seasonal = 0.3*Rpn + 0.7*Rpint = 0.84927, derated *0.93 (before_1980)
              = 0.78982
  Re = 0.95, Rd = 0.91, Rr = 0.90 (no thermostatic valves, old system)
  efficiency = 0.78982*0.95*0.91*0.90 = 0.61447
Intermittence: GV=994.83, G = 994.83/(2.5*100) = 3.9793
  INT = 0.87 / (1 + 0.1*(3.9793-1)) = 0.87/1.29793 = 0.67030
With Bch = 1000 kWh: Cch = 1000 * 0.67030 / 0.61447 = 1090.85 kWh

Electric joule (NF-certified emitters, calibration iteration 6):
  Rg=1, Re=0.95, Rd=1, Rr=0.99 -> eff = 0.9405
  INT (divided radiator, medium inertia -> light_medium 0.83):
  INT = 0.83/1.29793 = 0.63948 ; Cch(1000) = 1000*0.63948/0.9405 = 679.94 kWh

DHW electric storage (200 l, vertical unknown Cr=0.23, Rd=0.93 adjacent rooms):
  Qg,w = 8592*(45/24)*200*0.23 = 741 060 Wh = 741.06 kWh
  With Becs = 1500 kWh: Rs = 1/(1 + 741.06*0.93/1500) = 0.68519
  Cecs = 1500 / (1*0.93*0.68519) = 2354.0 kWh
"""

import pytest

from renosim.models import (
    Building,
    DHWGeneratorType,
    DHWSystem,
    EnergyCarrier,
    HeatingGeneratorType,
    HeatingSystem,
    InertiaClass,
)
from renosim.systems import (
    dhw_auxiliary_kwh,
    dhw_consumption,
    heating_auxiliary_kwh,
    heating_consumption,
    heating_system_efficiency,
)
from tests.test_envelope import _bare_house_kwargs
from tests.test_models import make_reference_building


def _house(**overrides: object) -> Building:
    kwargs = _bare_house_kwargs()
    kwargs.update(overrides)
    return make_reference_building(**kwargs)


def test_old_oil_boiler_efficiency_hand_computed() -> None:
    building = _house(
        heating_system=HeatingSystem(
            generator_type=HeatingGeneratorType.STANDARD_BOILER,
            energy_carrier=EnergyCarrier.FUEL_OIL,
            generator_age_years=50,
        )
    )
    eff = heating_system_efficiency(building)
    assert eff.overall == pytest.approx(0.61447, rel=1e-3)


def test_heating_consumption_hand_computed() -> None:
    building = _house(
        heating_system=HeatingSystem(
            generator_type=HeatingGeneratorType.STANDARD_BOILER,
            energy_carrier=EnergyCarrier.FUEL_OIL,
            generator_age_years=50,
        )
    )
    result = heating_consumption(building, heating_needs_kwh=1000.0)
    assert result.final_energy_kwh == pytest.approx(1090.85, rel=2e-3)
    assert result.energy_carrier is EnergyCarrier.FUEL_OIL


def test_electric_joule_consumption_hand_computed() -> None:
    building = _house(
        heating_system=HeatingSystem(
            generator_type=HeatingGeneratorType.ELECTRIC_JOULE,
            energy_carrier=EnergyCarrier.ELECTRICITY,
        )
    )
    result = heating_consumption(building, heating_needs_kwh=1000.0)
    assert result.final_energy_kwh == pytest.approx(679.94, rel=2e-3)


def test_heat_pump_beats_boiler() -> None:
    boiler = _house(
        heating_system=HeatingSystem(
            generator_type=HeatingGeneratorType.CONDENSING_BOILER,
            energy_carrier=EnergyCarrier.NATURAL_GAS,
            generator_age_years=2,
        )
    )
    pac = _house(
        heating_system=HeatingSystem(
            generator_type=HeatingGeneratorType.HEAT_PUMP_AIR_WATER,
            energy_carrier=EnergyCarrier.ELECTRICITY,
            generator_age_years=2,
        )
    )
    c_boiler = heating_consumption(boiler, heating_needs_kwh=10000.0)
    c_pac = heating_consumption(pac, heating_needs_kwh=10000.0)
    # SCOP 2.8 vs boiler ~1.0 => at least 2x less final energy
    assert c_pac.final_energy_kwh < c_boiler.final_energy_kwh / 2


def test_dhw_electric_storage_hand_computed() -> None:
    building = _house(
        dhw_system=DHWSystem(
            generator_type=DHWGeneratorType.ELECTRIC_STORAGE,
            energy_carrier=EnergyCarrier.ELECTRICITY,
        )
    )
    result = dhw_consumption(building, dhw_needs_kwh=1500.0)
    assert result.final_energy_kwh == pytest.approx(2354.0, rel=2e-3)
    assert result.energy_carrier is EnergyCarrier.ELECTRICITY


def test_dhw_heat_pump_water_heater_beats_electric_storage() -> None:
    electric = _house(
        dhw_system=DHWSystem(
            generator_type=DHWGeneratorType.ELECTRIC_STORAGE,
            energy_carrier=EnergyCarrier.ELECTRICITY,
        )
    )
    hpwh = _house(
        dhw_system=DHWSystem(
            generator_type=DHWGeneratorType.HEAT_PUMP_WATER_HEATER,
            energy_carrier=EnergyCarrier.ELECTRICITY,
        )
    )
    c_el = dhw_consumption(electric, dhw_needs_kwh=1500.0)
    c_hp = dhw_consumption(hpwh, dhw_needs_kwh=1500.0)
    assert c_hp.final_energy_kwh < c_el.final_energy_kwh


def test_consumption_strictly_positive() -> None:
    building = _house()
    assert heating_consumption(building, heating_needs_kwh=1.0).final_energy_kwh > 0
    assert dhw_consumption(building, dhw_needs_kwh=1.0).final_energy_kwh > 0


class TestHeatingAuxiliaries:
    """§15 auxiliaries, hand-computed on the bare reference house (GV=994.83,
    Sh=100, H1a low altitude):

    Circulator (§15.2.1): Tbase = -9.5 -> Pnc = 0.99483*29.5 = 29.3475 kW
      qv = 29.3475/(1.163*7.5) = 3.3646 m3/h
      Lem = 5*0.802*(1+sqrt(100)) = 44.11 m ; dP = 0.15*44.11+10 = 16.6165 kPa
      Pcirc = 6.44*(16.6165*3.3646)^0.676 = 6.44*15.180 = 97.76 W
    With 1000 h of heating: Caux_dist = 97.76 kWh.

    Generation (§15.1, oil boiler, Pn = 24 kW): Paux = 20+1.6*24 = 58.4 W
    With Bch = 12000 kWh: Qaux_g = 58.4*12000/24/1000 = 29.2 kWh.
    """

    def test_circulator_hand_computed(self) -> None:
        building = _house(
            heating_system=HeatingSystem(
                generator_type=HeatingGeneratorType.STANDARD_BOILER,
                energy_carrier=EnergyCarrier.FUEL_OIL,
                generator_age_years=50,
            )
        )
        # Zero needs isolate the circulator term (generation aux scales on Bch).
        aux = heating_auxiliary_kwh(building, heating_needs_kwh=0.0, heating_hours_h=1000.0)
        assert aux == pytest.approx(97.76, rel=2e-3)

    def test_generation_aux_hand_computed(self) -> None:
        building = _house(
            heating_system=HeatingSystem(
                generator_type=HeatingGeneratorType.STANDARD_BOILER,
                energy_carrier=EnergyCarrier.FUEL_OIL,
                generator_age_years=50,
            )
        )
        with_needs = heating_auxiliary_kwh(building, 12000.0, heating_hours_h=1000.0)
        without = heating_auxiliary_kwh(building, 0.0, heating_hours_h=1000.0)
        assert with_needs - without == pytest.approx(29.2, rel=1e-3)

    def test_divided_systems_have_no_heating_aux(self) -> None:
        joule = _house(
            heating_system=HeatingSystem(
                generator_type=HeatingGeneratorType.ELECTRIC_JOULE,
                energy_carrier=EnergyCarrier.ELECTRICITY,
            )
        )
        assert heating_auxiliary_kwh(joule, 12000.0, 5000.0) == 0.0

    def test_heat_pump_has_circulator_but_no_generation_aux(self) -> None:
        pac = _house(
            heating_system=HeatingSystem(
                generator_type=HeatingGeneratorType.HEAT_PUMP_AIR_WATER,
                energy_carrier=EnergyCarrier.ELECTRICITY,
                generator_age_years=0,
            )
        )
        # Same value with and without needs: only the circulator term remains.
        assert heating_auxiliary_kwh(pac, 12000.0, 1000.0) == pytest.approx(
            heating_auxiliary_kwh(pac, 0.0, 1000.0)
        )
        assert heating_auxiliary_kwh(pac, 0.0, 1000.0) > 0

    def test_dhw_aux_only_for_boiler_coupled_production(self) -> None:
        coupled = _house(
            heating_system=HeatingSystem(
                generator_type=HeatingGeneratorType.STANDARD_BOILER,
                energy_carrier=EnergyCarrier.FUEL_OIL,
                generator_age_years=50,
            ),
            dhw_system=DHWSystem(
                generator_type=DHWGeneratorType.COUPLED_TO_HEATING_SYSTEM,
                energy_carrier=EnergyCarrier.FUEL_OIL,
            ),
        )
        electric = _house(
            dhw_system=DHWSystem(
                generator_type=DHWGeneratorType.ELECTRIC_STORAGE,
                energy_carrier=EnergyCarrier.ELECTRICITY,
            )
        )
        # Paux = 58.4 W, Becs = 2400 kWh -> 58.4*2400/24/1000 = 5.84 kWh
        assert dhw_auxiliary_kwh(coupled, 2400.0) == pytest.approx(5.84, rel=1e-3)
        assert dhw_auxiliary_kwh(electric, 2400.0) == 0.0


class TestInertiaIntermittence:
    def test_heavy_inertia_raises_i0(self) -> None:
        # §8 table: central radiator I0 = 0.87 (light/medium) vs 0.89 (heavy).
        light = _house(inertia=InertiaClass.MEDIUM)
        heavy = _house(inertia=InertiaClass.HEAVY)
        assert heating_system_efficiency(light).intermittence_i0 == pytest.approx(0.87)
        assert heating_system_efficiency(heavy).intermittence_i0 == pytest.approx(0.89)


def test_intermittence_uses_declared_ceiling_height() -> None:
    # Bare house GV = 994.83 W/K (test_envelope). G = GV/(Hsp*Sh):
    #   Hsp 2.5 -> G = 3.9793 -> INT = I0/(1 + 0.1*2.9793) = I0/1.29793
    #   Hsp 3.0 -> G = 3.3161 -> INT = I0/(1 + 0.1*2.3161) = I0/1.23161
    # Ratio INT(3.0)/INT(2.5) = 1.29793/1.23161 = 1.05385
    from renosim.systems import intermittence_factor

    low = intermittence_factor(_house(), 1.0)
    high = intermittence_factor(_house(ceiling_height_m=3.0), 1.0)
    assert high / low == pytest.approx(1.05385, rel=1e-4)
