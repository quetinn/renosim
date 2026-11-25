"""Conversions to primary energy, CO2 emissions, DPE labels and energy costs."""

from __future__ import annotations

from datetime import date
from typing import Literal, cast

from renosim.models import AltitudeClass, ClimateZone, EnergyCarrier
from renosim.tables_io import load_table

RegulationVintage = Literal["dpe_2021", "dpe_2026", "dpe_2027"]
REGULATION_VINTAGES: tuple[RegulationVintage, ...] = ("dpe_2021", "dpe_2026", "dpe_2027")


def regulation_vintage_in_force(on: date) -> RegulationVintage:
    """DPE primary-energy convention in force on a given date (D-13).

    Reads ``regulation_vintage_schedule`` of tables/emission_factors.json: the
    latest entry whose ``from`` date is not after ``on``; dates before the
    first entry get the first convention.
    """
    entries = load_table("emission_factors")["regulation_vintage_schedule"]["entries"]
    chosen = str(entries[0]["vintage"])
    for entry in entries:
        if date.fromisoformat(str(entry["from"])) <= on:
            chosen = str(entry["vintage"])
    return cast(RegulationVintage, chosen)


#: Convention used when the caller does not pick one: the one in force on the
#: day the engine is loaded (in the app: the day the page is opened).
DEFAULT_REGULATION_VINTAGE: RegulationVintage = regulation_vintage_in_force(date.today())
EnergyUse = Literal["heating", "dhw", "cooling", "lighting", "auxiliaries"]

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
        ``"dpe_2021"`` (electricity factor 2.3, DPEs issued 2021-2025),
        ``"dpe_2026"`` (1.9, 2026) or ``"dpe_2027"`` (1.7, from 2027-01-01).
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


def _is_high_altitude_cold_zone(
    zone: ClimateZone, altitude: AltitudeClass, variant: dict[str, object]
) -> bool:
    zones = variant["applies_to_zones"]
    assert isinstance(zones, list)
    return altitude is AltitudeClass.HIGH and zone.value in zones


def _interp_small_surface(values: list[float], surfaces: list[float], surface_m2: float) -> float:
    """Threshold bound at ``surface_m2``, linearly interpolated between rows.

    ``values`` and ``surfaces`` are parallel (surfaces ascending, index 0 =
    the '<= 8 m2' row). A surface below the first row clamps to it; the table
    stops at 40 m2 (callers only use it for surfaces <= 40).
    """
    if surface_m2 <= surfaces[0]:
        return values[0]
    for i in range(len(surfaces) - 1):
        lo, hi = surfaces[i], surfaces[i + 1]
        if lo <= surface_m2 <= hi:
            frac = (surface_m2 - lo) / (hi - lo)
            return values[i] + (values[i + 1] - values[i]) * frac
    return values[-1]


def _thresholds(
    zone: ClimateZone, altitude: AltitudeClass, surface_m2: float | None
) -> dict[str, dict[str, float]]:
    """Resolve the label bounds for a dwelling, surface-dependent when <= 40 m2.

    ``surface_m2`` None (or > 40) uses the large-surface tables; <= 40 m2 uses
    the surface-interpolated small-surface tables (arrêté 25/03/2024). In high
    altitude cold zones only the E and F bounds are relaxed.
    """
    table = load_table("dpe_thresholds")
    high_alt = _is_high_altitude_cold_zone(zone, altitude, table["high_altitude_cold_zones"])

    if surface_m2 is None or surface_m2 > 40.0:
        variant = table["high_altitude_cold_zones"] if high_alt else table["standard"]
        return variant  # type: ignore[no-any-return]

    small = table["small_surface_le_40m2"]
    surfaces = small["surfaces_m2"]

    def resolve(axis: str) -> dict[str, float]:
        std = small["standard"][axis]
        bounds = {
            label: _interp_small_surface(std[label], surfaces, surface_m2) for label in _LABELS
        }
        if high_alt:
            ha = small["high_altitude_cold_zones"][axis]
            for label in ("E", "F"):
                bounds[label] = _interp_small_surface(ha[label], surfaces, surface_m2)
        return bounds

    return {
        "primary_energy_upper_kwhep_m2y": resolve("primary_energy_upper_kwhep_m2y"),
        "co2_upper_kgco2_m2y": resolve("co2_upper_kgco2_m2y"),
    }


def dpe_label(
    cep_kwhep_m2y: float,
    eges_kgco2_m2y: float,
    zone: ClimateZone,
    altitude: AltitudeClass,
    living_area_m2: float | None = None,
) -> str:
    """DPE label (A-G): worst of the energy and climate classifications.

    Values are compared after rounding down to the integer, per annexe 5
    ('valeurs arrondies à l'entier inférieur'); upper bounds are exclusive.

    Parameters
    ----------
    living_area_m2
        Reference surface in m2. When <= 40 m2 the surface-dependent thresholds
        of the arrêté du 25 mars 2024 apply; ``None`` (default) or > 40 m2 uses
        the standard large-surface tables.
    """
    thresholds = _thresholds(zone, altitude, living_area_m2)
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
                    total += float(bracket["fixed_eur"]) + float(bracket["rate_eur_per_kwh"]) * kwh
                    break
        else:
            total += float(flat[_flat_key[carrier]]) * kwh
    return total
