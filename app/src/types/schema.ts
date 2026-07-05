/**
 * TypeScript mirror of the JSON schema spoken by `renosim.bridge` (engine side).
 * Single source of truth for the wire format: any change here must be paired
 * with a change in engine/renosim/bridge.py and a SCHEMA_VERSION bump.
 */

export const SCHEMA_VERSION = "0.1";

// ── Enumerations (values are the engine's StrEnum values) ───────────────────

export type ClimateZone = "H1a" | "H1b" | "H1c" | "H2a" | "H2b" | "H2c" | "H2d" | "H3";

export type AltitudeClass = "low" | "medium" | "high";

export type ConstructionPeriod =
  | "before_1948"
  | "1948_1974"
  | "1975_1977"
  | "1978_1982"
  | "1983_1988"
  | "1989_2000"
  | "2001_2005"
  | "2006_2012"
  | "after_2013";

export type EnergyCarrier =
  | "electricity"
  | "natural_gas"
  | "fuel_oil"
  | "wood_logs"
  | "wood_pellets"
  | "district_heating";

export type HeatingGeneratorType =
  | "standard_boiler"
  | "low_temperature_boiler"
  | "condensing_boiler"
  | "electric_joule"
  | "heat_pump_air_water"
  | "heat_pump_air_air"
  | "wood_pellet_stove"
  | "wood_boiler"
  | "district_heating_substation";

export type DHWGeneratorType =
  | "electric_storage"
  | "gas_storage_or_instant"
  | "heat_pump_water_heater"
  | "coupled_to_heating_system";

export type VentilationType =
  | "natural"
  | "exhaust_only_manual"
  | "exhaust_only_hygro_a"
  | "exhaust_only_hygro_b"
  | "balanced_heat_recovery";

export type Glazing =
  | "single_glazing"
  | "double_glazing_old"
  | "double_glazing_recent"
  | "double_glazing_low_e"
  | "triple_glazing";

export type Adjacency = "detached" | "one_shared_wall" | "two_shared_walls";

export type InsulationState = "uninsulated" | "period_default" | "renovated" | "known_r";

export type RegulationVintage = "dpe_2021" | "dpe_2026";

export type DpeClass = "A" | "B" | "C" | "D" | "E" | "F" | "G";

// ── Input payload ────────────────────────────────────────────────────────────

export interface InsulationSpec {
  state: InsulationState;
  r_value_m2k_per_w?: number;
}

export interface BuildingInput {
  living_area_m2: number;
  levels: number;
  construction_period: ConstructionPeriod;
  climate_zone: ClimateZone;
  altitude_class: AltitudeClass;
  adjacency: Adjacency;
  wall_insulation: InsulationSpec;
  roof_insulation: InsulationSpec;
  floor_insulation: InsulationSpec;
  glazing: Glazing;
  heating: { generator: HeatingGeneratorType; carrier: EnergyCarrier; age_years: number | null };
  dhw: { generator: DHWGeneratorType; carrier?: EnergyCarrier | null };
  ventilation: { type: VentilationType; installed_after_2012?: boolean };
  occupants?: number;
}

export interface OccupancyInput {
  mode: "conventional" | "personalized";
  heating_setpoint_c?: number;
  occupants?: number;
  dhw_liters_per_day_per_adult?: number;
  energy_prices_eur_per_kwh?: Partial<Record<EnergyCarrier, number>>;
}

export type MeasureInput =
  | { type: "wall_insulation"; added_r_m2k_per_w?: number }
  | { type: "roof_insulation"; added_r_m2k_per_w?: number }
  | { type: "window_replacement"; glazing?: Glazing }
  | { type: "ventilation_upgrade"; new_type?: VentilationType }
  | { type: "heating_replacement"; new_generator?: HeatingGeneratorType }
  | { type: "dhw_upgrade" };

export type MeasureType = MeasureInput["type"];

export interface ScenarioInput {
  id: string;
  measures: MeasureInput[];
}

export interface SimulationPayload {
  schema_version: typeof SCHEMA_VERSION;
  regulation_vintage?: RegulationVintage;
  building: BuildingInput;
  occupancy: OccupancyInput;
  scenarios: ScenarioInput[];
}

// ── Output payload ───────────────────────────────────────────────────────────

export interface EnvelopeBreakdown {
  walls_w_per_k: number;
  roof_w_per_k: number;
  floor_w_per_k: number;
  windows_w_per_k: number;
  thermal_bridges_w_per_k: number;
  ventilation_w_per_k: number;
  infiltration_w_per_k: number;
  total_w_per_k: number;
}

export interface SimulationResult {
  is_conventional: boolean;
  /** Null on personalized runs: the DPE label always comes from the conventional run. */
  label: DpeClass | null;
  energy_class: DpeClass | null;
  climate_class: DpeClass | null;
  primary_energy_kwh_m2: number;
  final_energy_kwh_m2: number;
  co2_kg_m2: number;
  annual_cost_eur: number;
  final_energy_kwh_by_use: Record<"heating" | "dhw" | "auxiliaries" | "lighting", number>;
  final_energy_kwh_by_carrier: Partial<Record<EnergyCarrier, number>>;
  needs: { heating_kwh: number; dhw_kwh: number };
  envelope: EnvelopeBreakdown;
}

export interface ScenarioAssessment {
  investment_low_eur: number;
  investment_high_eur: number;
  annual_savings_eur: number;
  annual_energy_savings_kwh: number;
  annual_co2_savings_kg: number;
  payback_years_low: number | null;
  payback_years_high: number | null;
  after: SimulationResult;
}

export interface ScenarioOutput {
  id: string;
  measures: MeasureInput[];
  conventional: ScenarioAssessment;
  personalized: ScenarioAssessment | null;
}

export interface SimulationOutput {
  schema_version: string;
  engine: { name: string; version: string };
  baseline: {
    conventional: SimulationResult;
    personalized: SimulationResult | null;
  };
  scenarios: ScenarioOutput[];
  measure_costs: Record<MeasureType, { low_eur: number; high_eur: number }>;
  bundles: Record<string, MeasureInput[]>;
}
