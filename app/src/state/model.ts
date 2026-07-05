/**
 * App-side state model: the guided-form state, its period-derived defaults and
 * its serialisation to the engine's JSON schema. No business calculation here —
 * only input collection and mapping (CLAUDE.md §3).
 */

import { climateZoneFromPostalCode } from "../data/climateZones";
import {
  SCHEMA_VERSION,
  type AltitudeClass,
  type Adjacency,
  type BuildingInput,
  type ConstructionPeriod,
  type DHWGeneratorType,
  type EnergyCarrier,
  type Glazing,
  type HeatingGeneratorType,
  type InsulationSpec,
  type MeasureInput,
  type MeasureType,
  type OccupancyInput,
  type RegulationVintage,
  type ScenarioInput,
  type SimulationPayload,
  type VentilationType,
} from "../types/schema";

// ── Heating: curated generator+carrier combos for the form ──────────────────

export type HeatingChoice =
  | "gas_standard"
  | "gas_condensing"
  | "oil_boiler"
  | "electric_joule"
  | "heat_pump_air_water"
  | "heat_pump_air_air"
  | "wood_pellet_stove"
  | "wood_boiler"
  | "district_heating";

export const HEATING_SYSTEMS: Record<
  HeatingChoice,
  { generator: HeatingGeneratorType; carrier: EnergyCarrier }
> = {
  gas_standard: { generator: "standard_boiler", carrier: "natural_gas" },
  gas_condensing: { generator: "condensing_boiler", carrier: "natural_gas" },
  oil_boiler: { generator: "standard_boiler", carrier: "fuel_oil" },
  electric_joule: { generator: "electric_joule", carrier: "electricity" },
  heat_pump_air_water: { generator: "heat_pump_air_water", carrier: "electricity" },
  heat_pump_air_air: { generator: "heat_pump_air_air", carrier: "electricity" },
  wood_pellet_stove: { generator: "wood_pellet_stove", carrier: "wood_pellets" },
  wood_boiler: { generator: "wood_boiler", carrier: "wood_logs" },
  district_heating: { generator: "district_heating_substation", carrier: "district_heating" },
};

export type HeatingAgeChoice = "recent" | "mid" | "old" | "unknown";

/** Representative ages (years) for the efficiency-bracket lookup. */
export const HEATING_AGE_YEARS: Record<HeatingAgeChoice, number | null> = {
  recent: 3,
  mid: 10,
  old: 25,
  unknown: null,
};

export type InsulationChoice = { state: "uninsulated" | "period_default" | "renovated" } | {
  state: "known_r";
  rValue: number;
};

// ── Form state ───────────────────────────────────────────────────────────────

export interface FormState {
  postalCode: string;
  altitude: AltitudeClass;
  livingArea: number;
  period: ConstructionPeriod;
  levels: number;
  adjacency: Adjacency;
  wallInsulation: InsulationChoice;
  roofInsulation: InsulationChoice;
  floorInsulation: InsulationChoice;
  glazing: Glazing;
  heating: HeatingChoice;
  heatingAge: HeatingAgeChoice;
  dhw: DHWGeneratorType;
  ventilation: VentilationType;
}

export interface OccupancyState {
  mode: "conventional" | "personalized";
  setpointC: number;
  occupants: number;
  electricityPrice: number | null;
  heatingCarrierPrice: number | null;
}

/** Per-measure adjustable parameters for the scenario cards. */
export interface MeasureParams {
  wallAddedR: number;
  roofAddedR: number;
  windowGlazing: Glazing;
  ventilationTarget: VentilationType;
  heatingTarget: "heat_pump_air_water" | "condensing_boiler" | "wood_pellet_stove";
}

export const DEFAULT_MEASURE_PARAMS: MeasureParams = {
  wallAddedR: 3.7,
  roofAddedR: 7.0,
  windowGlazing: "double_glazing_low_e",
  ventilationTarget: "exhaust_only_hygro_b",
  heatingTarget: "heat_pump_air_water",
};

/** Prefills derived from the construction period (input defaults, not physics). */
export function defaultsForPeriod(period: ConstructionPeriod): Partial<FormState> {
  const pre1975 = period === "before_1948" || period === "1948_1974";
  const recent = period === "2006_2012" || period === "after_2013";
  const modern = period === "2001_2005" || recent;
  return {
    wallInsulation: { state: pre1975 ? "uninsulated" : "period_default" },
    roofInsulation: { state: pre1975 ? "uninsulated" : "period_default" },
    floorInsulation: { state: pre1975 ? "uninsulated" : "period_default" },
    glazing: recent ? "double_glazing_low_e" : modern ? "double_glazing_recent" : pre1975 ? "single_glazing" : "double_glazing_old",
    ventilation: pre1975 ? "natural" : recent ? "exhaust_only_hygro_b" : "exhaust_only_manual",
    heating: recent ? "gas_condensing" : "gas_standard",
    heatingAge: recent ? "recent" : "old",
    dhw: "coupled_to_heating_system",
  };
}

export const INITIAL_FORM: FormState = {
  postalCode: "",
  altitude: "low",
  livingArea: 100,
  period: "1948_1974",
  levels: 1,
  adjacency: "detached",
  ...(defaultsForPeriod("1948_1974") as Pick<
    FormState,
    | "wallInsulation"
    | "roofInsulation"
    | "floorInsulation"
    | "glazing"
    | "ventilation"
    | "heating"
    | "heatingAge"
    | "dhw"
  >),
};

export const INITIAL_OCCUPANCY: OccupancyState = {
  mode: "conventional",
  setpointC: 19,
  occupants: 3,
  electricityPrice: null,
  heatingCarrierPrice: null,
};

// ── Serialisation to the engine schema ───────────────────────────────────────

function insulationSpec(choice: InsulationChoice): InsulationSpec {
  if (choice.state === "known_r") {
    return { state: "known_r", r_value_m2k_per_w: choice.rValue };
  }
  return { state: choice.state };
}

export function buildingInput(form: FormState): BuildingInput {
  const zone = climateZoneFromPostalCode(form.postalCode);
  if (!zone) {
    throw new Error(`Code postal invalide ou hors métropole : ${form.postalCode}`);
  }
  const heating = HEATING_SYSTEMS[form.heating];
  return {
    living_area_m2: form.livingArea,
    levels: form.levels,
    construction_period: form.period,
    climate_zone: zone,
    altitude_class: form.altitude,
    adjacency: form.adjacency,
    wall_insulation: insulationSpec(form.wallInsulation),
    roof_insulation: insulationSpec(form.roofInsulation),
    floor_insulation: insulationSpec(form.floorInsulation),
    glazing: form.glazing,
    heating: {
      generator: heating.generator,
      carrier: heating.carrier,
      age_years: HEATING_AGE_YEARS[form.heatingAge],
    },
    dhw: { generator: form.dhw },
    ventilation: { type: form.ventilation },
  };
}

export function occupancyInput(occupancy: OccupancyState, form: FormState): OccupancyInput {
  if (occupancy.mode === "conventional") return { mode: "conventional" };
  const prices: Partial<Record<EnergyCarrier, number>> = {};
  if (occupancy.electricityPrice != null) prices.electricity = occupancy.electricityPrice;
  const carrier = HEATING_SYSTEMS[form.heating].carrier;
  if (occupancy.heatingCarrierPrice != null && carrier !== "electricity") {
    prices[carrier] = occupancy.heatingCarrierPrice;
  }
  return {
    mode: "personalized",
    heating_setpoint_c: occupancy.setpointC,
    occupants: occupancy.occupants,
    ...(Object.keys(prices).length > 0 ? { energy_prices_eur_per_kwh: prices } : {}),
  };
}

export function measureInput(type: MeasureType, params: MeasureParams): MeasureInput {
  switch (type) {
    case "wall_insulation":
      return { type, added_r_m2k_per_w: params.wallAddedR };
    case "roof_insulation":
      return { type, added_r_m2k_per_w: params.roofAddedR };
    case "window_replacement":
      return { type, glazing: params.windowGlazing };
    case "ventilation_upgrade":
      return { type, new_type: params.ventilationTarget };
    case "heating_replacement":
      return { type, new_generator: params.heatingTarget };
    case "dhw_upgrade":
      return { type };
  }
}

export const MEASURE_ORDER: MeasureType[] = [
  "roof_insulation",
  "wall_insulation",
  "window_replacement",
  "heating_replacement",
  "dhw_upgrade",
  "ventilation_upgrade",
];

/**
 * One scenario per active measure, plus a combined "bouquet" scenario when at
 * least two measures are active — the non-additivity of savings becomes
 * visible by comparing the bouquet to the sum of individual rows.
 */
export function scenariosInput(
  active: ReadonlySet<MeasureType>,
  params: MeasureParams,
): ScenarioInput[] {
  const singles: ScenarioInput[] = MEASURE_ORDER.filter((t) => active.has(t)).map((t) => ({
    id: t,
    measures: [measureInput(t, params)],
  }));
  if (active.size >= 2) {
    singles.push({
      id: "bouquet",
      measures: MEASURE_ORDER.filter((t) => active.has(t)).map((t) => measureInput(t, params)),
    });
  }
  return singles;
}

export function simulationPayload(
  form: FormState,
  occupancy: OccupancyState,
  active: ReadonlySet<MeasureType>,
  params: MeasureParams,
  vintage: RegulationVintage,
): SimulationPayload {
  return {
    schema_version: SCHEMA_VERSION,
    regulation_vintage: vintage,
    building: buildingInput(form),
    occupancy: occupancyInput(occupancy, form),
    scenarios: scenariosInput(active, params),
  };
}
