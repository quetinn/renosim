"""Conversions to primary energy, CO2 emissions, DPE labels and energy costs."""

from __future__ import annotations

from typing import Literal

from renosim.models import AltitudeClass, ClimateZone, EnergyCarrier
from renosim.tables_io import load_table

RegulationVintage = Literal["dpe_2021", "dpe_2026"]
EnergyUse = Literal["heating", "dhw", "lighting", "auxiliaries"]

_CARRIER_KEY = {
    EnergyCarrier.ELECTRICITY: "electricity",
    EnergyCarrier.NATURAL_GAS: "natural_gas",
    EnergyCarrier.FUEL_OIL: "fuel_oil",
    EnergyCarrier.WOOD_LOGS: "wood_logs",
    EnergyCarrier.WOOD_PELLETS: "wood_pellets",
    EnergyCarrier.DISTRICT_HEATING: "district_heating",
}

_LABELS = ("A", "B", "C", "D", "E", "F")


def primary_energy_kwh(
    final_energy_kwh: float, carrier: EnergyCarrier, vintage: RegulationVintage
) -> float:
    """Convert final energy to primary energy per the DPE convention.

    Parameters
    ----------
    final_energy_kwh
        Final energy in kWh.
    carrier
        Energy carrier.
    vintage
        ``"dpe_2021"`` (electricity factor 2.3, DPEs issued 2021-2025) or
        ``"dpe_2026"`` (1.9, in force since 2026-01-01).
    """
    factors = load_table("emission_factors")["primary_energy_factor"][vintage]
    if carrier is EnergyCarrier.ELECTRICITY:
        return final_energy_kwh * float(factors["electricity"])
    return final_energy_kwh * float(factors["default_other"])


def co2_emissions_kg(final_energy_kwh: float, carrier: EnergyCarrier, use: EnergyUse) -> float:
    """CO2 emissions (kgCO2eq) for a final energy amount, per carrier and use."""
    co2 = load_table("emission_factors")["co2_kg_per_kwh"]
    entry = co2[_CARRIER_KEY[carrier]]
    if carrier is EnergyCarrier.ELECTRICITY:
        return final_energy_kwh * float(entry[use])
    if carrier is EnergyCarrier.DISTRICT_HEATING:
        return final_energy_kwh * float(entry["value"])
    return final_energy_kwh * float(entry)


def _thresholds(zone: ClimateZone, altitude: AltitudeClass) -> dict[str, dict[str, float]]:
    table = load_table("dpe_thresholds")
    variant = table["high_altitude_cold_zones"]
    if altitude is AltitudeClass.HIGH and zone.value in variant["applies_to_zones"]:
        return variant  # type: ignore[no-any-return]
    return table["standard"]  # type: ignore[no-any-return]


def dpe_label(
    cep_kwhep_m2y: float,
    eges_kgco2_m2y: float,
    zone: ClimateZone,
    altitude: AltitudeClass,
) -> str:
    """DPE label (A-G): worst of the energy and climate classifications.

    Values are compared after rounding down to the integer, per annexe 5
    ('valeurs arrondies à l'entier inférieur'); upper bounds are exclusive.
    """
    thresholds = _thresholds(zone, altitude)
    cep = float(int(cep_kwhep_m2y))
    eges = float(int(eges_kgco2_m2y))

    def classify(value: float, bounds: dict[str, float]) -> str:
        for label in _LABELS:
            if value < float(bounds[label]):
                return label
        return "G"

    energy_class = classify(cep, thresholds["primary_energy_upper_kwhep_m2y"])
    climate_class = classify(eges, thresholds["co2_upper_kgco2_m2y"])
    return max(energy_class, climate_class)


def annual_energy_cost_eur(final_energy_by_carrier: dict[EnergyCarrier, float]) -> float:
    """Annual energy cost (EUR TTC) per the DPE conventional tariffs.

    Electricity and natural gas use the bracket formulas ``fixed + rate*kWh``;
    other carriers use flat rates. Tariff vintage: see energy_prices.json.
    """
    prices = load_table("energy_prices")
    flat = prices["flat_rates_eur_per_kwh"]
    brackets = prices["bracket_formulas"]
    _flat_key = {
        EnergyCarrier.FUEL_OIL: "fuel_oil",
        EnergyCarrier.DISTRICT_HEATING: "district_heating",
        EnergyCarrier.WOOD_PELLETS: "wood_pellets",
        EnergyCarrier.WOOD_LOGS: "wood_logs",
    }

    total = 0.0
    for carrier, kwh in final_energy_by_carrier.items():
        if kwh <= 0:
            continue
        if carrier in (EnergyCarrier.ELECTRICITY, EnergyCarrier.NATURAL_GAS):
            key = "electricity" if carrier is EnergyCarrier.ELECTRICITY else "natural_gas"
            for bracket in brackets[key]:
                max_kwh = bracket["max_kwh"]
                if max_kwh is None or kwh < float(max_kwh):
                    fixed = bracket["fixed_eur"]
                    total += (float(fixed) if fixed is not None else 94.0) + float(
                        bracket["rate_eur_per_kwh"]
                    ) * kwh
                    break
        else:
            total += float(flat[_flat_key[carrier]]) * kwh
    return total
