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
  | "wood_log_stove"
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

export type FloorType =
  | "unknown"
  | "terre_plein"
  | "vide_sanitaire"
  | "sous_sol_non_chauffe"
  | "local_non_chauffe";

export type GlazingOrientation = "unknown" | "south" | "east_west" | "north";

export type SolarShading = "clear_or_unknown" | "partial" | "heavy";

/** Thermal inertia class (3CL §6.1 utilization-factor exponent); unknown = medium. */
export type InertiaClass = "unknown" | "light" | "medium" | "heavy";

export type DwellingType = "house" | "apartment";

/** Apartment floor position; unknown behaves as an intermediate floor (D-18). */
export type ApartmentPosition = "ground" | "intermediate" | "top" | "unknown";

/** Optional user-known surface areas overriding the M-1 geometric reconstruction. */
export interface GeometryOverrides {
  ceiling_height_m?: number;
  wall_area_m2?: number;
  window_area_m2?: number;
  roof_area_m2?: number;
  floor_area_m2?: number;
}

export type InsulationState = "uninsulated" | "period_default" | "renovated" | "known_r";

/** Keys of engine/renosim/tables/insulation_materials.json (λ values live there). */
export type InsulationMaterial =
  | "glass_wool"
  | "rock_wool"
  | "cellulose"
  | "wood_fiber"
  | "eps"
  | "xps"
  | "polyurethane"
  | "unknown";

/** Exterior solar protections of the S/E/W/roof bays (annexe 9, #16 brique 1). */
export type SolarProtectionLevel = "full" | "partial" | "none" | "unknown";

/** Official passive summer-comfort levels (annexe 9). */
export type SummerComfortLevel = "insufficient" | "medium" | "good";

/** Installation period of the cooling generator (SEER bracket, 3CL §10.3). */
export type CoolingPeriod = "before_2008" | "2008_2014" | "from_2015" | "unknown";

export type RegulationVintage = "dpe_2021" | "dpe_2026" | "dpe_2027";

/** UI choice: "current" lets the engine apply the convention in force today. */
export type VintageChoice = "current" | RegulationVintage;

export type DpeClass = "A" | "B" | "C" | "D" | "E" | "F" | "G";

// ── Input payload ────────────────────────────────────────────────────────────

export interface InsulationSpec {
  state: InsulationState;
  /** known_r only — either an explicit R, or a material + thickness (R = e/λ engine-side). */
  r_value_m2k_per_w?: number;
  material?: InsulationMaterial;
  thickness_cm?: number;
}

export interface BuildingInput {
  living_area_m2: number;
  levels: number;
  construction_period: ConstructionPeriod;
  climate_zone: ClimateZone;
  altitude_class: AltitudeClass;
  dwelling_type?: DwellingType;
  apartment?: { position?: ApartmentPosition; traversant?: boolean };
  adjacency: Adjacency;
  wall_insulation: InsulationSpec;
  roof_insulation: InsulationSpec;
  floor_insulation: InsulationSpec;
  floor_type?: FloorType;
  glazing: Glazing;
  glazing_orientation?: GlazingOrientation;
  solar_shading?: SolarShading;
  inertia?: InertiaClass;
  geometry?: GeometryOverrides;
  heating: { generator: HeatingGeneratorType; carrier: EnergyCarrier; age_years: number | null };
  /** Heavy floor / ceiling / walls (3CL §7.4); overrides `inertia` when present. */
  inertia_elements?: {
    heavy_floor: boolean | null;
    heavy_ceiling: boolean | null;
    heavy_walls: boolean | null;
  };
  /** Wood stove/insert used as back-up: 25 % of the heating need (3CL §9.3). */
  heating_backup?: { generator: "wood_log_stove" | "wood_pellet_stove"; age_years?: number | null } | null;
  dhw: { generator: DHWGeneratorType; carrier?: EnergyCarrier | null };
  ventilation: { type: VentilationType; installed_after_2012?: boolean };
  /** Summer-comfort inputs (#16 brique 1); the roof criterion reuses roof_insulation. */
  summer?: {
    solar_protections?: SolarProtectionLevel;
    fixed_air_circulators?: boolean;
    air_conditioning?: boolean;
    air_conditioning_period?: CoolingPeriod;
  };
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
  | {
      type: "wall_insulation";
      added_r_m2k_per_w?: number;
      material?: InsulationMaterial;
      thickness_cm?: number;
    }
  | {
      type: "roof_insulation";
      added_r_m2k_per_w?: number;
      material?: InsulationMaterial;
      thickness_cm?: number;
    }
  | { type: "window_replacement"; glazing?: Glazing }
  | { type: "ventilation_upgrade"; new_type?: VentilationType }
  | { type: "heating_replacement"; new_generator?: HeatingGeneratorType }
  | { type: "dhw_upgrade" }
  | { type: "solar_protection_installation" };

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
  /** Opt-in label-target search (63 extra simulations engine-side, backlog #8). */
  label_targets?: { measures?: MeasureInput[] };
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
  final_energy_kwh_by_use: Record<
    "heating" | "dhw" | "cooling" | "auxiliaries" | "lighting",
    number
  >;
  final_energy_kwh_by_carrier: Partial<Record<EnergyCarrier, number>>;
  /** cooling_kwh is the conventional NEED Bfr — an indicator even without AC. */
  needs: { heating_kwh: number; dhw_kwh: number; cooling_kwh: number };
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

/** Passive summer-comfort assessment (annexe 9, #16 brique 1). */
export interface SummerComfortOutput {
  level: SummerComfortLevel;
  criteria: {
    /** False for an apartment without a deperditive ceiling (criterion skipped). */
    roof_criterion_applicable: boolean;
    roof_insulated: boolean;
    solar_protections_full: boolean;
    heavy_inertia: boolean;
    through_dwelling: boolean;
    fixed_air_circulators: boolean;
  };
}

/** Needed heating power vs the heat-pump cost reference (audit §4.4). */
export interface HeatPumpSizing {
  /** Pnc = GV·(20 − Tbase)/1000 after the scenario's envelope measures (kW). */
  design_heat_load_kw: number;
  reference_power_low_kw: number;
  reference_power_high_kw: number;
  /** Needed power above the range the displayed heat-pump cost refers to. */
  above_reference: boolean;
}

export interface ScenarioOutput {
  id: string;
  measures: MeasureInput[];
  conventional: ScenarioAssessment;
  personalized: ScenarioAssessment | null;
  summer_comfort_after: SummerComfortOutput;
  /** Null unless the scenario installs a new air-to-water heat pump. */
  heat_pump_sizing: HeatPumpSizing | null;
}

/** Standalone conventional preview of one measure on the current building. */
export interface MeasurePreview {
  annual_savings_eur: number;
  annual_energy_savings_kwh: number;
  annual_co2_savings_kg: number;
  payback_years_low: number | null;
  payback_years_high: number | null;
  after_label: DpeClass | null;
  summer_comfort_level_after: SummerComfortLevel;
  heat_pump_sizing: HeatPumpSizing | null;
}

/** Cheapest measure combination reaching a target DPE class (conventional mode). */
export interface LabelTargetEntry {
  measures: MeasureInput[];
  investment_low_eur: number;
  investment_high_eur: number;
  annual_savings_eur: number;
  annual_co2_savings_kg: number;
  payback_years_low: number | null;
  payback_years_high: number | null;
  after_label: DpeClass;
  after_primary_energy_kwh_m2: number;
}

export interface SimulationOutput {
  schema_version: string;
  engine: { name: string; version: string };
  /** Conventions the engine applied to this run (for display). */
  conventions: {
    regulation_vintage: RegulationVintage;
    electricity_primary_energy_factor: number;
    energy_prices: { label: string; date_reference: string; date_in_force: string };
    /** Works costs are indexed to this month with the INSEE BT01 index. */
    renovation_costs: { index: string; reference_period: string };
  };
  baseline: {
    /** Heating power needed at the base temperature (3CL §15.2.2), kW. */
    design_heat_load_kw: number;
    conventional: SimulationResult;
    personalized: SimulationResult | null;
  };
  summer_comfort: SummerComfortOutput & {
    air_conditioning: boolean;
    /** Conventional cooling need Bfr (28 °C) — "what summer would cost if cooled". */
    cooling_need_kwh: number;
    cooling_need_kwh_m2: number;
  };
  scenarios: ScenarioOutput[];
  measure_costs: Record<MeasureType, { low_eur: number; high_eur: number }>;
  measure_previews: Record<MeasureType, MeasurePreview>;
  bundles: Record<string, MeasureInput[]>;
  /** Null when the payload did not request the label-target search. */
  label_targets: Partial<Record<DpeClass, LabelTargetEntry>> | null;
}
