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


class TestLighting:
    """3CL §16.1: Cecl = sum_j C * Pecl * Nh_j / 1000, Nh_j per zone and month (p.102-103)."""

    def test_h1a_hand_computed(self) -> None:
        # H1a: Nh = 1500 h/an ; 0.9 * 1.4 * 1500 / 1000 = 1.89 kWh/m2 -> 100 m2 = 189.0 kWh
        from renosim.systems import lighting_kwh

        assert lighting_kwh(_house()) == pytest.approx(189.0)

    def test_h2c_hand_computed(self) -> None:
        # H2c: Nh = 1566 h/an ; 0.9 * 1.4 * 1566 * 100 / 1000 = 197.316 kWh
        from renosim.models import ClimateZone
        from renosim.systems import lighting_kwh

        assert lighting_kwh(_house(climate_zone=ClimateZone.H2C)) == pytest.approx(197.316)

    def test_monthly_table_matches_published_totals(self) -> None:
        # Annual totals printed under the official table (p.103).
        from renosim.tables_io import load_table

        nh = load_table("system_efficiencies")["lighting"]["nh_hours_by_zone_month"]
        totals = {"H1a": 1500, "H1b": 1445, "H1c": 1476, "H2a": 1500,
                  "H2b": 1531, "H2c": 1566, "H2d": 1566, "H3": 1506}  # fmt: skip
        for zone, total in totals.items():
            assert sum(nh[zone].values()) == total, zone


def test_design_heat_load_hand_computed() -> None:
    """Pnc = GV * (20 - Tbase) / 1000 (3CL §15.2.2, Tbase §18.1).

    Reference house (H1a, altitude < 400 m): GV = 994.83 W/K, Tbase = -9.5 degC
      Pnc = 994.83 * 29.5 / 1000 = 29.348 kW
    Same house in H3 above 800 m: Tbase = -7.5 degC -> 994.83 * 27.5 / 1000 = 27.358 kW
    (GV does not depend on the zone).
    """
    from dataclasses import replace

    from renosim.models import AltitudeClass, ClimateZone
    from renosim.systems import design_heat_load_kw
    from tests.test_reference_cases import house_1970_oil_uninsulated

    house = house_1970_oil_uninsulated()
    assert design_heat_load_kw(house) == pytest.approx(29.348, abs=0.001)
    h3_high = replace(house, climate_zone=ClimateZone.H3, altitude_class=AltitudeClass.HIGH)
    assert design_heat_load_kw(h3_high) == pytest.approx(27.358, abs=0.001)


def test_wood_log_stove_efficiency_hand_computed() -> None:
    """Wood-log stove / insert (3CL §13.1, p.78): Rg by installation period.

    Age -> period with reference year 2026 (tables/conventions.json):
      40 y (installed ~1986) -> before 1990          Rg 0.50
      25 y (~2001)           -> 1990-2004            Rg 0.60
      10 y (~2016)           -> 2005-2017, label     Rg 0.70
       3 y (~2023)           -> from 2018, label     Rg 0.75
      unknown                -> 2005-2017, label     Rg 0.70
    Re 0.95 (other equipment), Rd 1 (no network), Rr 0.80 (stove or insert):
      overall(10 y) = 0.70 * 0.95 * 1 * 0.80 = 0.532
    """

    def stove(age: float | None) -> Building:
        return _house(
            heating_system=HeatingSystem(
                HeatingGeneratorType.WOOD_LOG_STOVE, EnergyCarrier.WOOD_LOGS, age
            )
        )

    for age, rg in ((40.0, 0.50), (25.0, 0.60), (10.0, 0.70), (3.0, 0.75), (None, 0.70)):
        assert heating_system_efficiency(stove(age)).generation == pytest.approx(rg)
    eff = heating_system_efficiency(stove(10.0))
    assert (eff.emission, eff.distribution, eff.regulation) == pytest.approx((0.95, 1.0, 0.80))
    assert eff.overall == pytest.approx(0.532)
    # No hydraulic network: no circulator, no generation auxiliaries.
    assert heating_auxiliary_kwh(stove(10.0), 10_000.0, 5_000.0) == 0.0


def test_wood_backup_splits_heating_75_25_hand_computed() -> None:
    """Insert or wood stove used as back-up (3CL §9.3, p.62).

    Cch1 = 0.75 * Bch * INT1 * Ich1 (main system), Cch2 = 0.25 * Bch * INT2 * Ich2.
    Reference house (GV 994.83 W/K, G = 3.9793), Bch = 1000 kWh:
      main = electric joule: INT1 = 0.83/1.29793 = 0.63948, Ich1 = 1/0.9405
        Cch1 = 750 * 0.63948 / 0.9405 = 509.95 kWh electricity
      back-up = wood-log stove, 10 y: I0 0.83 (divided) -> INT2 = 0.63948,
        Ich2 = 1/0.532 -> Cch2 = 250 * 0.63948 / 0.532 = 300.51 kWh wood logs
    """
    from renosim.systems import heating_backup_consumption

    house = _house(
        heating_system=HeatingSystem(
            HeatingGeneratorType.ELECTRIC_JOULE, EnergyCarrier.ELECTRICITY, 10.0
        ),
        heating_backup=HeatingSystem(
            HeatingGeneratorType.WOOD_LOG_STOVE, EnergyCarrier.WOOD_LOGS, 10.0
        ),
    )
    main = heating_consumption(house, 1000.0)
    backup = heating_backup_consumption(house, 1000.0)
    assert main.energy_carrier is EnergyCarrier.ELECTRICITY
    assert main.final_energy_kwh == pytest.approx(509.95, abs=0.01)
    assert backup is not None
    assert backup.energy_carrier is EnergyCarrier.WOOD_LOGS
    assert backup.final_energy_kwh == pytest.approx(300.51, abs=0.01)
    # Without a back-up the main system covers everything and there is no back-up line.
    alone = _house(
        heating_system=HeatingSystem(
            HeatingGeneratorType.ELECTRIC_JOULE, EnergyCarrier.ELECTRICITY, 10.0
        )
    )
    assert heating_backup_consumption(alone, 1000.0) is None
    assert heating_consumption(alone, 1000.0).final_energy_kwh == pytest.approx(679.94, abs=0.01)


def test_wood_backup_must_be_a_stove() -> None:
    with pytest.raises(ValueError, match="heating_backup"):
        _house(
            heating_backup=HeatingSystem(
                HeatingGeneratorType.CONDENSING_BOILER, EnergyCarrier.NATURAL_GAS, 5.0
            )
        )


def test_wood_boiler_efficiency_hand_computed() -> None:
    """Wood boilers, 3CL §13.2.2.3 (p.89-90), Pn = 24 kW (log10 Pn = 1.38021),
    seasonal Rg = 0.3*Rpn + 0.7*Rpint (same approximation as gas/oil, D-08).

    Logs, installed after 2019 (3 y; 20 < Pn <= 70 row):
      Rpn = 90 + 2*1.38021 = 92.760 ; Rpint = 85 + 2.760 = 87.760
      Rg = (0.3*92.760 + 0.7*87.760)/100 = 0.89260
    Logs, 2004-2012 (18 y): Rpn 57 + 6 log = 65.281 ; Rpint 66.281 -> Rg 0.65981
    Logs, before 2004 (40 y): Rpn 47 + 6 log = 55.281 ; Rpint 56.281 -> Rg 0.55981
    Pellets, 2013-2019 (10 y): Rpn 80 + 2.760 = 82.760 ; Rpint 77 + 3*1.38021 = 81.141
      -> Rg 0.81627
    Hydraulic chain like a boiler: Re 0.95, Rd 0.91, Rr 0.95 (recent):
      overall(logs, 3 y) = 0.89260*0.95*0.91*0.95 = 0.73307
    """

    def boiler(carrier: EnergyCarrier, age: float | None) -> Building:
        return _house(heating_system=HeatingSystem(HeatingGeneratorType.WOOD_BOILER, carrier, age))

    logs, pellets = EnergyCarrier.WOOD_LOGS, EnergyCarrier.WOOD_PELLETS
    for carrier, age, rg in (
        (logs, 3.0, 0.89260),
        (logs, 18.0, 0.65981),
        (logs, 40.0, 0.55981),
        (pellets, 10.0, 0.81627),
    ):
        assert heating_system_efficiency(boiler(carrier, age)).generation == pytest.approx(
            rg, abs=1e-5
        )
    eff = heating_system_efficiency(boiler(logs, 3.0))
    assert eff.overall == pytest.approx(0.73307, abs=1e-5)
    # A wood boiler has a hydraulic network: circulator auxiliaries are counted.
    assert heating_auxiliary_kwh(boiler(logs, 3.0), 10_000.0, 5_000.0) > 0.0
