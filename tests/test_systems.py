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

Electric joule: Rg=1, Re=0.95, Rd=1, Rr=0.96 -> eff = 0.912
  INT (divided radiator, medium inertia -> light_medium 0.83):
  INT = 0.83/1.29793 = 0.63948 ; Cch(1000) = 1000*0.63948/0.912 = 701.19 kWh

DHW electric storage (200 l, vertical unknown Cr=0.23, Rd=0.87):
  Qg,w = 8592*(45/24)*200*0.23 = 741 060 Wh = 741.06 kWh
  With Becs = 1500 kWh: Rs = 1/(1 + 741.06*0.87/1500) = 0.69946
  Cecs = 1500 / (1*0.87*0.69946) = 2464.9 kWh
"""

import pytest

from renosim.models import (
    Building,
    DHWGeneratorType,
    DHWSystem,
    EnergyCarrier,
    HeatingGeneratorType,
    HeatingSystem,
)
from renosim.systems import dhw_consumption, heating_consumption, heating_system_efficiency
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
    assert result.final_energy_kwh == pytest.approx(701.19, rel=2e-3)


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
    assert result.final_energy_kwh == pytest.approx(2464.9, rel=2e-3)
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
