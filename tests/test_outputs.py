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


def test_energy_cost_flat_and_brackets() -> None:
    # fuel oil flat rate: 10 000 kWh * 0.09142 = 914.2 EUR
    assert annual_energy_cost_eur({EnergyCarrier.FUEL_OIL: 10000.0}) == pytest.approx(914.2)
    # electricity 10 000 kWh -> bracket 5000-15000: 94 + 0.15735*10000 = 1667.5
    assert annual_energy_cost_eur({EnergyCarrier.ELECTRICITY: 10000.0}) == pytest.approx(1667.5)
    # natural gas 20 000 kWh -> bracket 2: 230 + 0.06533*20000 = 1536.6
    assert annual_energy_cost_eur({EnergyCarrier.NATURAL_GAS: 20000.0}) == pytest.approx(1536.6)
