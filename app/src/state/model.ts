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
  type ApartmentPosition,
  type BuildingInput,
  type CoolingPeriod,
  type DwellingType,
  type ConstructionPeriod,
  type DHWGeneratorType,
  type EnergyCarrier,
  type FloorType,
  type GeometryOverrides,
  type Glazing,
  type GlazingOrientation,
  type HeatingGeneratorType,
  type InertiaClass,
  type InsulationMaterial,
  type InsulationSpec,
  type MeasureInput,
  type MeasureType,
  type OccupancyInput,
  type VintageChoice,
  type ScenarioInput,
  type SimulationPayload,
  type SolarProtectionLevel,
  type SolarShading,
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
  | "wood_log_stove"
  | "wood_boiler"
  | "wood_pellet_boiler"
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
  wood_log_stove: { generator: "wood_log_stove", carrier: "wood_logs" },
  wood_boiler: { generator: "wood_boiler", carrier: "wood_logs" },
  wood_pellet_boiler: { generator: "wood_boiler", carrier: "wood_pellets" },
  district_heating: { generator: "district_heating_substation", carrier: "district_heating" },
};

export type HeatingAgeChoice = "recent" | "mid" | "old" | "unknown";

/** Wood stove/insert used alongside the main heating (3CL §9.3). */
export type HeatingBackupChoice = "none" | "wood_log_stove" | "wood_pellet_stove";

/** Main heating choices that are themselves wood appliances (no wood back-up asked). */
export const WOOD_MAIN_HEATING: readonly HeatingChoice[] = [
  "wood_pellet_stove",
  "wood_log_stove",
  "wood_boiler",
  "wood_pellet_boiler",
];

/** Representative ages (years) for the efficiency-bracket lookup. */
export const HEATING_AGE_YEARS: Record<HeatingAgeChoice, number | null> = {
  recent: 3,
  mid: 10,
  old: 25,
  unknown: null,
};

export type InsulationChoice =
  | { state: "uninsulated" | "period_default" | "renovated" }
  | { state: "known_r"; material: InsulationMaterial; thicknessCm: number };

// ── Form state ───────────────────────────────────────────────────────────────

/** Optional user-known surfaces; null = derive from the M-1 reconstruction. */
export interface GeometryState {
  ceilingHeight: number | null;
  wallArea: number | null;
  windowArea: number | null;
  roofArea: number | null;
  floorArea: number | null;
}

export const EMPTY_GEOMETRY: GeometryState = {
  ceilingHeight: null,
  wallArea: null,
  windowArea: null,
  roofArea: null,
  floorArea: null,
};

export interface FormState {
  postalCode: string;
  altitude: AltitudeClass;
  livingArea: number;
  period: ConstructionPeriod;
  dwellingType: DwellingType;
  apartmentPosition: ApartmentPosition;
  apartmentTraversant: boolean;
  levels: number;
  adjacency: Adjacency;
  geometry: GeometryState;
  wallInsulation: InsulationChoice;
  roofInsulation: InsulationChoice;
  floorInsulation: InsulationChoice;
  floorType: FloorType;
  glazing: Glazing;
  glazingOrientation: GlazingOrientation;
  solarShading: SolarShading;
  inertia: InertiaClass;
  heating: HeatingChoice;
  heatingAge: HeatingAgeChoice;
  heatingBackup: HeatingBackupChoice;
  dhw: DHWGeneratorType;
  ventilation: VentilationType;
  /** Confort d'été (#16 brique 1) : volets/BSO, brasseurs d'air fixes, clim.
   * "unknown" n'est pas proposé au formulaire (directement observable, D-19). */
  solarProtections: Exclude<SolarProtectionLevel, "unknown">;
  fixedAirCirculators: boolean;
  airConditioning: boolean;
  /** Période d'installation de la clim (tranche SEER §10.3, brique 2). */
  airConditioningPeriod: CoolingPeriod;
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
  wallMaterial: InsulationMaterial;
  wallThicknessCm: number;
  roofMaterial: InsulationMaterial;
  roofThicknessCm: number;
  windowGlazing: Glazing;
  ventilationTarget: VentilationType;
  heatingTarget: "heat_pump_air_water" | "condensing_boiler" | "wood_pellet_stove";
}

// Glass wool at λ=0.040: 15 cm ≈ R 3.75, 28 cm = R 7.0 — the usual
// "performant" levels (matches the engine's default added R of 3.7 / 7).
export const DEFAULT_MEASURE_PARAMS: MeasureParams = {
  wallMaterial: "glass_wool",
  wallThicknessCm: 15,
  roofMaterial: "glass_wool",
  roofThicknessCm: 28,
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
  dwellingType: "house",
  apartmentPosition: "unknown",
  apartmentTraversant: true,
  levels: 1,
  adjacency: "detached",
  geometry: EMPTY_GEOMETRY,
  floorType: "unknown",
  glazingOrientation: "unknown",
  solarShading: "clear_or_unknown",
  inertia: "unknown",
  // Volets quasi systématiques sur l'habitat français : défaut « oui »,
  // corrigeable en un clic (l'engin traite « unknown » comme « full », D-19).
  solarProtections: "full",
  fixedAirCirculators: false,
  airConditioning: false,
  airConditioningPeriod: "from_2015",
  heatingBackup: "none",
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
    return { state: "known_r", material: choice.material, thickness_cm: choice.thicknessCm };
  }
  return { state: choice.state };
}

function geometryInput(geometry: GeometryState): GeometryOverrides | undefined {
  // Empty or non-positive fields fall back to the engine's M-1 reconstruction.
  const overrides: GeometryOverrides = {};
  const set = (key: keyof GeometryOverrides, value: number | null) => {
    if (value != null && value > 0) overrides[key] = value;
  };
  set("ceiling_height_m", geometry.ceilingHeight);
  set("wall_area_m2", geometry.wallArea);
  set("window_area_m2", geometry.windowArea);
  set("roof_area_m2", geometry.roofArea);
  set("floor_area_m2", geometry.floorArea);
  return Object.keys(overrides).length > 0 ? overrides : undefined;
}

export function buildingInput(form: FormState): BuildingInput {
  const zone = climateZoneFromPostalCode(form.postalCode);
  if (!zone) {
    throw new Error(`Code postal invalide ou hors métropole : ${form.postalCode}`);
  }
  const heating = HEATING_SYSTEMS[form.heating];
  const geometry = geometryInput(form.geometry);
  return {
    living_area_m2: form.livingArea,
    levels: form.levels,
    construction_period: form.period,
    climate_zone: zone,
    altitude_class: form.altitude,
    dwelling_type: form.dwellingType,
    ...(form.dwellingType === "apartment"
      ? {
          apartment: {
            position: form.apartmentPosition,
            traversant: form.apartmentTraversant,
          },
        }
      : {}),
    adjacency: form.adjacency,
    ...(geometry ? { geometry } : {}),
    wall_insulation: insulationSpec(form.wallInsulation),
    roof_insulation: insulationSpec(form.roofInsulation),
    floor_insulation: insulationSpec(form.floorInsulation),
    floor_type: form.floorType,
    glazing: form.glazing,
    glazing_orientation: form.glazingOrientation,
    solar_shading: form.solarShading,
    inertia: form.inertia,
    heating: {
      generator: heating.generator,
      carrier: heating.carrier,
      age_years: HEATING_AGE_YEARS[form.heatingAge],
    },
    heating_backup:
      form.heatingBackup !== "none" && !WOOD_MAIN_HEATING.includes(form.heating)
        ? { generator: form.heatingBackup }
        : null,
    dhw: { generator: form.dhw },
    ventilation: { type: form.ventilation },
    summer: {
      solar_protections: form.solarProtections,
      fixed_air_circulators: form.fixedAirCirculators,
      air_conditioning: form.airConditioning,
      air_conditioning_period: form.airConditioningPeriod,
    },
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
      return { type, material: params.wallMaterial, thickness_cm: params.wallThicknessCm };
    case "roof_insulation":
      return { type, material: params.roofMaterial, thickness_cm: params.roofThicknessCm };
    case "window_replacement":
      return { type, glazing: params.windowGlazing };
    case "ventilation_upgrade":
      return { type, new_type: params.ventilationTarget };
    case "heating_replacement":
      return { type, new_generator: params.heatingTarget };
    case "dhw_upgrade":
      return { type };
    case "solar_protection_installation":
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
  "solar_protection_installation",
];

/** Gestes explorés par la recherche d'étiquette cible (le geste « été pur »
 * ne peut pas améliorer l'étiquette — il doublerait juste l'espace 2^n). */
export const LABEL_TARGET_MEASURES: MeasureType[] = MEASURE_ORDER.filter(
  (t) => t !== "solar_protection_installation",
);

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
  vintage: VintageChoice,
  includeLabelTargets = false,
): SimulationPayload {
  return {
    schema_version: SCHEMA_VERSION,
    // "current": omitted, the engine applies the convention in force today.
    ...(vintage === "current" ? {} : { regulation_vintage: vintage }),
    building: buildingInput(form),
    occupancy: occupancyInput(occupancy, form),
    scenarios: scenariosInput(active, params),
    // Label-target search over the six energy measures with the current card
    // params (63 combinations engine-side) — only on the scenarios screen.
    ...(includeLabelTargets
      ? {
          label_targets: {
            measures: LABEL_TARGET_MEASURES.map((t) => measureInput(t, params)),
          },
        }
      : {}),
  };
}
