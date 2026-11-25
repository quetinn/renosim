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
from typing import Any

from renosim.envelope import ceiling_height_m, conventional_airflows, envelope_heat_loss
from renosim.models import (
    Building,
    ClimateZone,
    DHWGeneratorType,
    DwellingType,
    EnergyCarrier,
    HeatingGeneratorType,
    InertiaClass,
    VentilationType,
)
from renosim.tables_io import load_table

#: Weight of the full-load efficiency in the V1 seasonal blend (0.3 Rpn + 0.7
#: Rpint): residential load profiles are dominated by part-load operation
#: (3CL §13.2.1.1 load-profile weights). Deviation D-08, tables/conventions.json.
FULL_LOAD_WEIGHT = float(
    load_table("conventions")["boiler_seasonal_blend"]["full_load_weight"]["value"]
)


def _age_conventions() -> dict[str, Any]:
    conventions: dict[str, Any] = load_table("conventions")["generator_age_brackets"]
    return conventions


def _bracket_by_age(name: str, age_years: float | None) -> Any:
    """Installation-period key for a generator age (tables/conventions.json).

    Rules are ordered by decreasing ``min_age_years``; the first match wins and
    an unknown age returns the table's ``unknown`` entry (audit §4.9).
    """
    rules = _age_conventions()[name]
    if age_years is None:
        return rules["unknown"]
    for rule in rules["rules"]:
        if age_years >= float(rule["min_age_years"]):
            return rule["bracket"]
    raise ValueError(f"negative generator age: {age_years}")  # pragma: no cover


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


def _i0(i0_table: dict[str, dict[str, float]], emitter_key: str, building: Building) -> float:
    """I0 per emitter configuration and inertia column (§8 tables, p.55-56).

    Houses: ``HEAVY`` selects the "inertie lourde ou très lourde" column; every
    other inertia class (including UNKNOWN) uses the light/medium column, which
    is the calibrated V1 behaviour. Apartments use the "immeuble collectif,
    chauffage individuel" table, which has no inertia split.
    """
    if building.dwelling_type is DwellingType.APARTMENT:
        apartment = load_table("system_efficiencies")["intermittence"]["i0_apartment_individual"]
        return float(apartment[emitter_key])
    column = "heavy" if building.inertia is InertiaClass.HEAVY else "light_medium"
    return float(i0_table[emitter_key][column])


def _age_bracket_pac(age_years: float | None) -> str:
    """Installation-period bracket for heat pumps from the generator age."""
    return str(_bracket_by_age("heat_pump_scop", age_years))


def _boiler_seasonal_rg(building: Building) -> float:
    """Seasonal generation efficiency of gas/oil boilers (deviation D-08)."""
    table = load_table("system_efficiencies")["boiler_efficiency_formulas"]
    pn_kw = float(table["default_nominal_power_kw"])
    log_pn = math.log10(pn_kw)
    gtype = building.heating_system.generator_type
    age = building.heating_system.generator_age_years

    recent_max_age = float(_age_conventions()["condensing_boiler_recent_max_age_years"])
    if gtype is HeatingGeneratorType.LOW_TEMPERATURE_BOILER:
        family = "low_temperature"
    elif gtype is HeatingGeneratorType.CONDENSING_BOILER:
        recent = age is not None and age < recent_max_age
        family = "condensing_2016_plus_le_70kw" if recent else "condensing_pre_2016"
    else:  # standard / classique
        family = "standard"
    coefs = table["log10_pn_coefficients"][family]
    rpn = float(coefs["rpn"][0]) + float(coefs["rpn"][1]) * log_pn
    rpint = float(coefs["rpint"][0]) + float(coefs["rpint"][1]) * log_pn

    rg = (FULL_LOAD_WEIGHT * rpn + (1.0 - FULL_LOAD_WEIGHT) * rpint) / 100.0

    derating = load_table("system_efficiencies")["boiler_efficiency_formulas"][
        "old_boiler_derating"
    ]
    if gtype is HeatingGeneratorType.STANDARD_BOILER:
        bracket = _bracket_by_age("standard_boiler_derating", age)
        if bracket is not None:
            rg *= float(derating[bracket])
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
    old_system = age is not None and age >= float(
        _age_conventions()["no_thermostatic_valves_min_age_years"]
    )

    if gtype is HeatingGeneratorType.ELECTRIC_JOULE:
        # Conventional assumption (calibration iteration 6): installed electric
        # emitters are overwhelmingly NF-certified -> Rr 0.99 (official value).
        return HeatingEfficiency(
            generation=float(eff["generation_rg_non_combustion"]["electric_joule_direct"]),
            emission=float(re_t["electric_convector"]),
            distribution=1.0,
            regulation=float(rr_t["electric_convector_nf"]),
            intermittence_i0=_i0(i0_t, "divided_radiator_convector", building),
        )

    if gtype in (
        HeatingGeneratorType.WOOD_PELLET_STOVE,
        HeatingGeneratorType.WOOD_BOILER,
    ):
        stoves = eff["stoves_rg"]["wood_pellet_stove"]
        rg = float(stoves[str(_bracket_by_age("pellet_stove_rg", age))])
        return HeatingEfficiency(
            generation=rg,
            emission=float(re_t["other_equipment"]),
            distribution=1.0,
            regulation=float(rr_t["stove_or_insert"]),
            intermittence_i0=_i0(i0_t, "divided_radiator_convector", building),
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
                intermittence_i0=_i0(i0_t, "central_radiator", building),
            )
        aa_bracket = "after_2015" if bracket in ("2015_2016", "after_2017") else bracket
        scop = float(scop_t["air_air"][group][aa_bracket])
        return HeatingEfficiency(
            generation=scop,
            emission=float(re_t["hot_air_blowing"]),
            distribution=float(rd_t["refrigerant_network"]),
            regulation=float(rr_t["blown_air"]),
            intermittence_i0=_i0(i0_t, "blown_air", building),
        )

    if gtype is HeatingGeneratorType.DISTRICT_HEATING_SUBSTATION:
        return HeatingEfficiency(
            generation=float(eff["generation_rg_non_combustion"]["district_heating"]),
            emission=float(re_t["other_equipment"]),
            distribution=float(rd_t["individual_water_low_temp"]["uninsulated"]),
            regulation=float(rr_t["water_radiator_without_thermostatic_valves"]),
            intermittence_i0=_i0(i0_t, "central_radiator", building),
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
        intermittence_i0=_i0(i0_t, "central_radiator", building),
    )


def intermittence_factor(building: Building, i0: float) -> float:
    """Intermittence factor INT = I0 / (1 + 0.1*(G-1)), G = GV/(Hsp*Sh)."""
    gv = envelope_heat_loss(building).gv_w_per_k
    g = gv / (ceiling_height_m(building) * building.living_area_m2)
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
    hours_h = float(storage["standby_hours_per_year_h"])
    delta_t_c = float(storage["storage_temperature_difference_c"])
    # Cr is a 24 h loss coefficient -> delta_t / 24 per standby hour.
    qgw_kwh = hours_h * (delta_t_c / 24.0) * volume_l * cr / 1000.0
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
    """Annual ventilation auxiliary consumption (kWh electricity, 3CL §5).

    Houses use the flat average powers Pvent_moy; apartments use the
    collective formula ``Pvent_moy = Pvent x Qvarep_conv x Sh`` with Pvent in
    W/(m3/h) (§5, p.41).
    """
    vtype = building.ventilation_system.ventilation_type
    if vtype in (VentilationType.NATURAL,):
        return 0.0
    recent = (
        building.ventilation_system.installed_after_2012
        or building.construction_period.value == "after_2013"
    )
    key = "after_2012" if recent else "until_2012"

    if building.dwelling_type is DwellingType.APARTMENT:
        aux_c = load_table("ventilation")["auxiliary_power_collective_w_per_m3h"]
        family = (
            "balanced_heat_recovery"
            if vtype is VentilationType.BALANCED_HEAT_RECOVERY
            else "exhaust_only"
        )
        pvent_w_per_m3h = float(aux_c[family][key])
        qvarep, _, _ = conventional_airflows(building)
        p = pvent_w_per_m3h * qvarep * building.living_area_m2
        return 8760.0 * p / 1000.0

    aux = load_table("ventilation")["auxiliary_power_house_w"]
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


#: Generators with a central hydraulic network -> heating circulator (§15.2).
#: Only these can also produce a boiler-coupled DHW (renovation.py).
HYDRAULIC_GENERATORS = frozenset(
    {
        HeatingGeneratorType.STANDARD_BOILER,
        HeatingGeneratorType.LOW_TEMPERATURE_BOILER,
        HeatingGeneratorType.CONDENSING_BOILER,
        HeatingGeneratorType.WOOD_BOILER,
        HeatingGeneratorType.HEAT_PUMP_AIR_WATER,
        HeatingGeneratorType.DISTRICT_HEATING_SUBSTATION,
    }
)

#: Combustion boilers with generation auxiliaries (burner fan/controls, §15.1).
_GENERATION_AUX_KEY = {
    HeatingGeneratorType.STANDARD_BOILER: "gas_or_oil_boiler",
    HeatingGeneratorType.LOW_TEMPERATURE_BOILER: "gas_or_oil_boiler",
    HeatingGeneratorType.CONDENSING_BOILER: "gas_or_oil_boiler",
    HeatingGeneratorType.WOOD_BOILER: "wood_boiler_atmospheric",
}


def _zone_group_tbase(zone: ClimateZone) -> str:
    if zone is ClimateZone.H3:
        return "H3"
    return "H1" if zone.value.startswith("H1") else "H2"


def _generation_aux_kwh(building: Building, needs_kwh: float) -> float:
    """Qaux_g = Paux_g * B_g / Pn with Paux_g = G + H*Pn (§15.1)."""
    key = _GENERATION_AUX_KEY.get(building.heating_system.generator_type)
    if key is None or needs_kwh <= 0:
        # Heat pumps (in the SCOP), district heating (conventionally zero),
        # joule and stoves (no central generation) have no generation aux.
        return 0.0
    eff = load_table("system_efficiencies")
    gh = eff["auxiliaries"]["generation_power_w"][key]
    pn_kw = float(eff["boiler_efficiency_formulas"]["default_nominal_power_kw"])
    paux_w = float(gh["g_w"]) + float(gh["h_w_per_kw"]) * pn_kw
    # Paux [W] x (B [kWh] / Pn [kW]) = full-load-equivalent hours x Paux -> Wh.
    return paux_w * needs_kwh / pn_kw / 1000.0


def heating_auxiliary_kwh(
    building: Building, heating_needs_kwh: float, heating_hours_h: float
) -> float:
    """Heating auxiliaries Caux_ch (kWh electricity, §15): generation + circulator.

    Parameters
    ----------
    building
        Building description.
    heating_needs_kwh
        Annual useful heating needs Bch (kWh), the share covered by the
        generator (100 % in V1, single-generator installations).
    heating_hours_h
        Annual heating-season hours Nref (h) — see
        :func:`renosim.needs.annual_heating_hours`.

    Notes
    -----
    Documented simplifications (D-11): radiators on a non-monotube network
    (delta_Pem 10 kPa), Fcot "autre", low/medium distribution temperature
    (delta_theta 7.5 degC), single served level, whole need on one generator.
    """
    total = _generation_aux_kwh(building, heating_needs_kwh)

    if building.heating_system.generator_type in HYDRAULIC_GENERATORS:
        aux = load_table("system_efficiencies")["auxiliaries"]
        circ = aux["circulator"]
        sh = building.living_area_m2
        gv = envelope_heat_loss(building).gv_w_per_k
        tbase = float(
            aux["base_temperature_c"][_zone_group_tbase(building.climate_zone)][
                building.altitude_class.value
            ]
        )
        heat_capacity = float(
            load_table("occupancy_conventional")["dhw"]["water_heat_capacity_wh_per_l_k"]
        )
        pnc_kw = gv * (20.0 - tbase) / 1000.0
        qv_m3_h = pnc_kw / (heat_capacity * float(circ["delta_theta_dim_c"]["low_medium_temp"]))
        lem_m = 5.0 * float(circ["fcot"]["other"]) * (1.0 + math.sqrt(sh))
        dp_kpa = float(circ["linear_pressure_loss_kpa_per_m"]) * lem_m + float(
            circ["emitter_pressure_loss_kpa"]["radiators"]
        )
        size_factor = max(1.0, sh / float(circ["sh_norm_m2"]))
        pcirc_w = max(
            float(circ["min_power_w"]),
            float(circ["power_coefficient"])
            * (dp_kpa * qv_m3_h / size_factor) ** float(circ["power_exponent"])
            * size_factor,
        )
        total += pcirc_w * heating_hours_h / 1000.0

    return total


def dhw_auxiliary_kwh(building: Building, dhw_needs_kwh: float) -> float:
    """DHW auxiliaries Caux_ecs (kWh electricity, §15.1.2).

    Individual DHW distribution auxiliaries are zero (§15.2.3); only the
    generation auxiliaries of a boiler-coupled production remain (heat-pump
    water heaters are in the COP, gas water heaters have G = H = 0).
    """
    if building.dhw_system.generator_type is not DHWGeneratorType.COUPLED_TO_HEATING_SYSTEM:
        return 0.0
    return _generation_aux_kwh(building, dhw_needs_kwh)


def lighting_kwh(building: Building) -> float:
    """Annual conventional lighting consumption (kWh electricity, 3CL §16.1).

    ``Cecl = sum_j C * Pecl * Nh_j * Sh / 1000`` with the monthly lighting hours
    Nh_j of the dwelling's climate zone (§16.1 table, 1445-1566 h/an).
    """
    cfg = load_table("system_efficiencies")["lighting"]
    monthly = cfg["nh_hours_by_zone_month"][building.climate_zone.value]
    annual_hours = sum(float(h) for h in monthly.values())
    return (
        float(cfg["c_switch_control"])
        * float(cfg["p_ecl_w_per_m2"])
        * annual_hours
        * building.living_area_m2
        / 1000.0
    )


def cooling_eer(building: Building) -> float:
    """Seasonal EER of the declared cooling generator (3CL §10.3).

    ``EER = 0.95 * SEER`` from the zone-group x installation-period table;
    the pre-2008 column is published as an EER directly. An unknown period
    uses the most recent bracket (D-20).
    """
    cooling = load_table("cooling")
    seer_table = cooling["seer"]
    group = _zone_group_scop(building.climate_zone)
    period = building.air_conditioning_period.value
    if period == "unknown":
        period = "from_2015"
    seer = float(seer_table[group][period])
    if period in seer_table["eer_direct_periods"]:
        return seer
    return float(cooling["eer_from_seer_factor"]) * seer


def cooling_consumption(building: Building, cooling_needs_kwh: float) -> UseConsumption:
    """Final cooling consumption Cfr (kWh electricity, 3CL §10.3).

    ``Cfr = 0.9 * Bfr / EER`` when an air conditioner is declared; zero
    otherwise (the need Bfr remains a physical indicator either way). V1
    assumes the whole dwelling is cooled (D-20).
    """
    if not building.has_air_conditioning or cooling_needs_kwh <= 0.0:
        return UseConsumption(final_energy_kwh=0.0, energy_carrier=EnergyCarrier.ELECTRICITY)
    intermittence = float(load_table("cooling")["intermittence"])
    final = intermittence * cooling_needs_kwh / cooling_eer(building)
    return UseConsumption(final_energy_kwh=final, energy_carrier=EnergyCarrier.ELECTRICITY)
