"""Tests for renosim.outputs — primary energy, CO2, DPE labels, energy costs.

Label thresholds (annexe 5, arrêté 31/03/2021): A <70/6, B <110/11, C <180/30,
D <250/50, E <330/70, F <420/100, G above. Final label = worst of the two.
"""

import pytest

from renosim.models import AltitudeClass, ClimateZone, EnergyCarrier
from renosim.outputs import (
    annual_energy_cost_eur,
    co2_emissions_kg,
    dpe_label,
    primary_energy_kwh,
)


def test_primary_energy_electricity_dpe_2021() -> None:
    # 1000 kWh_ef electricity -> 2300 kWhep under the 2021-2025 convention
    assert primary_energy_kwh(1000.0, EnergyCarrier.ELECTRICITY, "dpe_2021") == 2300.0
    assert primary_energy_kwh(1000.0, EnergyCarrier.ELECTRICITY, "dpe_2026") == 1900.0
    assert primary_energy_kwh(1000.0, EnergyCarrier.NATURAL_GAS, "dpe_2021") == 1000.0


def test_co2_emissions_per_use() -> None:
    # electricity heating: 0.079 kg/kWh ; DHW: 0.065 ; gas flat 0.227
    assert co2_emissions_kg(1000.0, EnergyCarrier.ELECTRICITY, "heating") == pytest.approx(79.0)
    assert co2_emissions_kg(1000.0, EnergyCarrier.ELECTRICITY, "dhw") == pytest.approx(65.0)
    assert co2_emissions_kg(1000.0, EnergyCarrier.NATURAL_GAS, "heating") == pytest.approx(227.0)
    assert co2_emissions_kg(1000.0, EnergyCarrier.FUEL_OIL, "heating") == pytest.approx(324.0)


@pytest.mark.parametrize(
    "cep,eges,expected",
    [
        (50, 5, "A"),
        (69, 6, "B"),  # EGES 6 is >= 6 -> class B on the CO2 axis
        (100, 5, "B"),
        (170, 25, "C"),
        (200, 10, "D"),  # energy drives
        (100, 60, "E"),  # CO2 drives
        (400, 90, "F"),
        (430, 20, "G"),
        (100, 120, "G"),
    ],
)
def test_dpe_label_standard(cep: float, eges: float, expected: str) -> None:
    label = dpe_label(cep, eges, ClimateZone.H1A, AltitudeClass.LOW)
    assert label == expected


def test_dpe_label_altitude_variant() -> None:
    # H1b > 800 m: E extends to 390 kWhep and 80 kgCO2
    assert dpe_label(380, 20, ClimateZone.H1B, AltitudeClass.HIGH) == "E"
    assert dpe_label(380, 20, ClimateZone.H1B, AltitudeClass.LOW) == "F"
    # but not for zones outside H1b/H1c/H2d
    assert dpe_label(380, 20, ClimateZone.H2A, AltitudeClass.HIGH) == "F"


class TestSmallSurfaceThresholds:
    """Surface-dependent thresholds for dwellings <= 40 m2 (arrêté 25/03/2024).

    Bounds read from the official annexe 5 tables §1.2.2 (rendered image,
    verbatim). All hand-computed from those tables.
    """

    def test_20m2_relaxes_the_class(self) -> None:
        # 20 m2 standard-altitude bounds: CEP A88 B128 C230 D300 E385 F476;
        # CO2 A8 B13 C34 D54 E74 F104. CEP=200 -> energy C (200<230); CO2=20 -> C.
        assert dpe_label(200, 20, ClimateZone.H1A, AltitudeClass.LOW, living_area_m2=20) == "C"
        # Same consumption evaluated as a large dwelling -> D (180<=200<250).
        assert dpe_label(200, 20, ClimateZone.H1A, AltitudeClass.LOW, living_area_m2=100) == "D"

    def test_below_8m2_clamps_to_the_first_row(self) -> None:
        # <= 8 m2 row: CEP_a=146, CEP_b=186, CO2_a=11.
        assert dpe_label(140, 5, ClimateZone.H1A, AltitudeClass.LOW, living_area_m2=6) == "A"
        assert dpe_label(150, 5, ClimateZone.H1A, AltitudeClass.LOW, living_area_m2=6) == "B"

    def test_exactly_40m2_uses_small_table_with_eges_d_55(self) -> None:
        # At 40 m2 the <=40 table gives EGES_d=55 (not the 50 of the >40 table).
        # CO2=52 -> climate D (52<55); CEP=60 low -> energy A/B; label D.
        assert dpe_label(60, 52, ClimateZone.H1A, AltitudeClass.LOW, living_area_m2=40) == "D"
        # Strictly above 40 m2 -> large table, EGES_d=50 -> 52>=50 -> climate E.
        assert dpe_label(60, 52, ClimateZone.H1A, AltitudeClass.LOW, living_area_m2=41) == "E"

    def test_linear_interpolation_between_rows(self) -> None:
        # CEP_c: row22=221, row23=217 -> 22.5 m2 = 219. CEP=218<219 -> energy C.
        assert dpe_label(218, 5, ClimateZone.H1A, AltitudeClass.LOW, living_area_m2=22.5) == "C"
        # At 24 m2 CEP_c=214 -> 218>=214 -> energy D.
        assert dpe_label(218, 5, ClimateZone.H1A, AltitudeClass.LOW, living_area_m2=24) == "D"

    def test_high_altitude_small_surface_relaxes_e_and_f(self) -> None:
        # 20 m2, H1c >800 m: CEP_e high-altitude bound = 445 (vs 385 standard).
        # CEP=440 -> E in high-altitude cold zone, F otherwise.
        assert dpe_label(440, 5, ClimateZone.H1C, AltitudeClass.HIGH, living_area_m2=20) == "E"
        assert dpe_label(440, 5, ClimateZone.H1C, AltitudeClass.LOW, living_area_m2=20) == "F"


def test_energy_cost_flat_and_brackets() -> None:
    # fuel oil flat rate: 10 000 kWh * 0.09142 = 914.2 EUR
    assert annual_energy_cost_eur({EnergyCarrier.FUEL_OIL: 10000.0}) == pytest.approx(914.2)
    # electricity 10 000 kWh -> bracket 5000-15000: 94 + 0.15735*10000 = 1667.5
    assert annual_energy_cost_eur({EnergyCarrier.ELECTRICITY: 10000.0}) == pytest.approx(1667.5)
    # natural gas 20 000 kWh -> bracket 2: 230 + 0.06533*20000 = 1536.6
    assert annual_energy_cost_eur({EnergyCarrier.NATURAL_GAS: 20000.0}) == pytest.approx(1536.6)
