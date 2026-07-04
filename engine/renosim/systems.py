"""System efficiencies: useful needs -> final energy consumption per use.

Heating (3CL §9/§12/§13, simplified): ``Cch = Bch * INT / (Rg*Re*Rd*Rr)``.
DHW (3CL §11/§14): ``Cecs = Becs / (Rg*Rd*Rs)`` (or ``Becs / (COP*Rd)`` for
heat-pump water heaters). V1 simplifications are documented in
docs/deviations.md (seasonal boiler efficiency from Rpn/Rpint blend, fixed
emitter assumptions per generator type).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from renosim.envelope import DEFAULT_CEILING_HEIGHT_M, envelope_heat_loss
from renosim.models import (
    Building,
    ClimateZone,
    DHWGeneratorType,
    EnergyCarrier,
    HeatingGeneratorType,
    VentilationType,
)
from renosim.tables_io import load_table

#: Weight of the full-load efficiency in the V1 seasonal blend (0.3 Rpn + 0.7
#: Rpint): residential load profiles are dominated by part-load operation
#: (3CL §13.2.1.1 load-profile weights). Deviation D-08.
FULL_LOAD_WEIGHT = 0.3


@dataclass(frozen=True, slots=True)
class HeatingEfficiency:
    """Efficiency chain of the heating installation (dimensionless)."""

    generation: float
    emission: float
    distribution: float
    regulation: float
    intermittence_i0: float

    @property
    def overall(self) -> float:
        """Product Rg*Re*Rd*Rr (excluding intermittence, applied on needs)."""
        return self.generation * self.emission * self.distribution * self.regulation


@dataclass(frozen=True, slots=True)
class UseConsumption:
    """Final energy consumption for one use (heating, DHW, ...)."""

    final_energy_kwh: float
    energy_carrier: EnergyCarrier


def _zone_group_scop(zone: ClimateZone) -> str:
    return "H3" if zone is ClimateZone.H3 else "H1_H2"


def _age_bracket_pac(age_years: float | None) -> str:
    """Installation-period bracket for heat pumps from the generator age."""
    if age_years is None:
        return "2008_2014"  # conservative middle bracket when unknown
    if age_years >= 18:
        return "before_2008"
    if age_years >= 11:
        return "2008_2014"
    if age_years >= 9:
        return "2015_2016"
    return "after_2017"


def _boiler_seasonal_rg(building: Building) -> float:
    """Seasonal generation efficiency of gas/oil boilers (deviation D-08)."""
    table = load_table("system_efficiencies")["boiler_efficiency_formulas"]
    pn_kw = float(table["default_nominal_power_kw"])
    log_pn = math.log10(pn_kw)
    gtype = building.heating_system.generator_type
    age = building.heating_system.generator_age_years

    if gtype is HeatingGeneratorType.LOW_TEMPERATURE_BOILER:
        rpn = rpint = 87.5 + 1.5 * log_pn
    elif gtype is HeatingGeneratorType.CONDENSING_BOILER:
        if age is not None and age < 10:
            rpn = 91.0 + 3.0 * log_pn
            rpint = 103.0 + 2.5 * log_pn
        else:
            rpn = 91.0 + 1.0 * log_pn
            rpint = 97.0 + 1.0 * log_pn
    else:  # standard / classique
        rpn = 84.0 + 2.0 * log_pn
        rpint = 80.0 + 3.0 * log_pn

    rg = (FULL_LOAD_WEIGHT * rpn + (1.0 - FULL_LOAD_WEIGHT) * rpint) / 100.0

    derating = load_table("system_efficiencies")["boiler_efficiency_formulas"][
        "old_boiler_derating"
    ]
    if gtype is HeatingGeneratorType.STANDARD_BOILER and age is not None:
        if age >= 45:
            rg *= float(derating["before_1980"])
        elif age >= 35:
            rg *= float(derating["1981_1990"])
    return rg


def heating_system_efficiency(building: Building) -> HeatingEfficiency:
    """Resolve the efficiency chain of the heating installation.

    V1 maps each generator type onto a conventional emitter configuration
    (documented deviation D-09): boilers/heat pumps -> individual water
    network with radiators; joule -> divided electric emitters; stoves -> no
    network.

    Returns
    -------
    HeatingEfficiency
        Efficiencies and the intermittence base I0.
    """
    eff = load_table("system_efficiencies")
    re_t = eff["emission_re"]
    rd_t = eff["distribution_rd_heating"]
    rr_t = eff["regulation_rr"]
    i0_t = eff["intermittence"]["i0_house_individual"]
    gtype = building.heating_system.generator_type
    age = building.heating_system.generator_age_years
    old_system = age is not None and age >= 25

    if gtype is HeatingGeneratorType.ELECTRIC_JOULE:
        # Conventional assumption (calibration iteration 6): installed electric
        # emitters are overwhelmingly NF-certified -> Rr 0.99 (official value).
        return HeatingEfficiency(
            generation=float(eff["generation_rg_non_combustion"]["electric_joule_direct"]),
            emission=float(re_t["electric_convector"]),
            distribution=1.0,
            regulation=float(rr_t["electric_convector_nf"]),
            intermittence_i0=float(i0_t["divided_radiator_convector"]["light_medium"]),
        )

    if gtype in (
        HeatingGeneratorType.WOOD_PELLET_STOVE,
        HeatingGeneratorType.WOOD_BOILER,
    ):
        stoves = eff["stoves_rg"]["wood_pellet_stove"]
        if age is None or age < 7:
            rg = float(stoves["after_2020_label"])
        elif age < 15:
            rg = float(stoves["2012_2019_label"])
        else:
            rg = float(stoves["before_2012_or_no_label"])
        return HeatingEfficiency(
            generation=rg,
            emission=float(re_t["other_equipment"]),
            distribution=1.0,
            regulation=float(rr_t["stove_or_insert"]),
            intermittence_i0=float(i0_t["divided_radiator_convector"]["light_medium"]),
        )

    if gtype in (
        HeatingGeneratorType.HEAT_PUMP_AIR_WATER,
        HeatingGeneratorType.HEAT_PUMP_AIR_AIR,
    ):
        scop_t = eff["heat_pump_scop"]
        group = _zone_group_scop(building.climate_zone)
        bracket = _age_bracket_pac(age)
        if gtype is HeatingGeneratorType.HEAT_PUMP_AIR_WATER:
            scop = float(scop_t["air_water"][group]["radiators"][bracket])
            return HeatingEfficiency(
                generation=scop,
                emission=float(re_t["other_equipment"]),
                distribution=float(rd_t["individual_water_low_temp"]["insulated"]),
                regulation=float(rr_t["water_radiator_with_thermostatic_valves"]),
                intermittence_i0=float(i0_t["central_radiator"]["light_medium"]),
            )
        aa_bracket = "after_2015" if bracket in ("2015_2016", "after_2017") else bracket
        scop = float(scop_t["air_air"][group][aa_bracket])
        return HeatingEfficiency(
            generation=scop,
            emission=float(re_t["hot_air_blowing"]),
            distribution=float(rd_t["refrigerant_network"]),
            regulation=float(rr_t["blown_air"]),
            intermittence_i0=float(i0_t["blown_air"]["light_medium"]),
        )

    if gtype is HeatingGeneratorType.DISTRICT_HEATING_SUBSTATION:
        return HeatingEfficiency(
            generation=float(eff["generation_rg_non_combustion"]["district_heating"]),
            emission=float(re_t["other_equipment"]),
            distribution=float(rd_t["individual_water_low_temp"]["uninsulated"]),
            regulation=float(rr_t["water_radiator_without_thermostatic_valves"]),
            intermittence_i0=float(i0_t["central_radiator"]["light_medium"]),
        )

    # Gas / oil boilers
    rr = (
        float(rr_t["water_radiator_without_thermostatic_valves"])
        if old_system
        else float(rr_t["water_radiator_with_thermostatic_valves"])
    )
    return HeatingEfficiency(
        generation=_boiler_seasonal_rg(building),
        emission=float(re_t["other_equipment"]),
        distribution=float(rd_t["individual_water_low_temp"]["uninsulated"]),
        regulation=rr,
        intermittence_i0=float(i0_t["central_radiator"]["light_medium"]),
    )


def intermittence_factor(building: Building, i0: float) -> float:
    """Intermittence factor INT = I0 / (1 + 0.1*(G-1)), G = GV/(Hsp*Sh)."""
    gv = envelope_heat_loss(building).gv_w_per_k
    g = gv / (DEFAULT_CEILING_HEIGHT_M * building.living_area_m2)
    return i0 / (1.0 + 0.1 * (g - 1.0))


def heating_consumption(building: Building, heating_needs_kwh: float) -> UseConsumption:
    """Final heating energy: Cch = Bch * INT / (Rg*Re*Rd*Rr)."""
    eff = heating_system_efficiency(building)
    intermittence = intermittence_factor(building, eff.intermittence_i0)
    final = heating_needs_kwh * intermittence / eff.overall
    return UseConsumption(
        final_energy_kwh=final, energy_carrier=building.heating_system.energy_carrier
    )


def dhw_consumption(building: Building, dhw_needs_kwh: float) -> UseConsumption:
    """Final DHW energy per generator type (3CL §11/§14, simplified).

    Electric storage: Rg=1, Rd individual, Rs from tank losses (200 l default).
    Heat-pump water heater: Iecs = 1/(Rd*COP). Coupled to heating: the heating
    generator's seasonal Rg with the same storage/distribution chain.
    """
    eff = load_table("system_efficiencies")["dhw"]
    # Conventional assumption (calibration iteration 6): production inside the
    # living space with adjacent bathroom/kitchen — the most common single-family
    # configuration (official Rd 0.93, annexe 1 §11.5.1).
    rd = float(eff["distribution_rd_individual"]["production_in_living_space_adjacent_rooms"])
    gtype = building.dhw_system.generator_type
    carrier = building.dhw_system.energy_carrier

    if gtype is DHWGeneratorType.HEAT_PUMP_WATER_HEATER:
        group = "H3" if building.climate_zone is ClimateZone.H3 else "H1_H2"
        cop = float(
            eff["heat_pump_water_heater_cop"][group]["outdoor_or_unheated_air"]["after_2015"]
        )
        final = dhw_needs_kwh / (rd * cop)
        return UseConsumption(final_energy_kwh=final, energy_carrier=EnergyCarrier.ELECTRICITY)

    # Storage losses (electric storage and coupled-with-tank cases)
    storage = eff["electric_storage_losses"]
    volume_l = float(storage["default_volume_l"])
    cr = float(storage["cr_vertical_unknown_by_volume"]["100_200"])
    qgw_kwh = 8592.0 * (45.0 / 24.0) * volume_l * cr / 1000.0
    rs = 1.0 / (1.0 + qgw_kwh * rd / dhw_needs_kwh) if dhw_needs_kwh > 0 else 1.0

    if gtype is DHWGeneratorType.ELECTRIC_STORAGE:
        rg = 1.0
    elif gtype is DHWGeneratorType.GAS_STORAGE_OR_INSTANT:
        rg = float(eff["gas_water_heater_rg"]["after_2000"])
    else:  # COUPLED_TO_HEATING_SYSTEM
        carrier = building.heating_system.energy_carrier
        heating_gen = heating_system_efficiency(building).generation
        rg = heating_gen
        if building.heating_system.generator_type is HeatingGeneratorType.ELECTRIC_JOULE:
            rg = 1.0

    final = dhw_needs_kwh / (rg * rd * rs)
    return UseConsumption(final_energy_kwh=final, energy_carrier=carrier)


def ventilation_auxiliary_kwh(building: Building) -> float:
    """Annual ventilation auxiliary consumption (kWh electricity, 3CL §5)."""
    vtype = building.ventilation_system.ventilation_type
    if vtype in (VentilationType.NATURAL,):
        return 0.0
    aux = load_table("ventilation")["auxiliary_power_house_w"]
    recent = (
        building.ventilation_system.installed_after_2012
        or building.construction_period.value == "after_2013"
    )
    key = "after_2012" if recent else "until_2012"
    if vtype is VentilationType.EXHAUST_ONLY_MANUAL:
        p = float(aux["exhaust_only_manual"][key])
    elif vtype in (
        VentilationType.EXHAUST_ONLY_HYGRO_A,
        VentilationType.EXHAUST_ONLY_HYGRO_B,
    ):
        p = float(aux["exhaust_only_hygro"][key])
    else:  # balanced
        p = float(aux["balanced_heat_recovery"][key])
    return 8760.0 * p / 1000.0


def lighting_kwh(building: Building) -> float:
    """Annual conventional lighting consumption (kWh electricity, 3CL §16.1)."""
    cfg = load_table("system_efficiencies")["lighting"]
    return (
        float(cfg["c_switch_control"])
        * float(cfg["p_ecl_w_per_m2"])
        * float(cfg["annual_hours_national_average"])
        * building.living_area_m2
        / 1000.0
    )
