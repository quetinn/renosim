import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useEngine } from "../pyodide/PyodideContext";
import type {
  MeasureInput,
  MeasureType,
  RegulationVintage,
  SimulationOutput,
} from "../types/schema";
import {
  DEFAULT_MEASURE_PARAMS,
  INITIAL_FORM,
  INITIAL_OCCUPANCY,
  defaultsForPeriod,
  simulationPayload,
  type FormState,
  type MeasureParams,
  type OccupancyState,
} from "./model";

export type View = "landing" | "form" | "results" | "scenarios";

interface AppStateValue {
  view: View;
  setView: (view: View) => void;

  form: FormState;
  updateForm: (patch: Partial<FormState>) => void;
  setPeriod: (period: FormState["period"]) => void;

  occupancy: OccupancyState;
  updateOccupancy: (patch: Partial<OccupancyState>) => void;

  activeMeasures: ReadonlySet<MeasureType>;
  toggleMeasure: (type: MeasureType) => void;
  applyBundle: (measures: MeasureInput[]) => void;
  clearMeasures: () => void;

  params: MeasureParams;
  updateParams: (patch: Partial<MeasureParams>) => void;

  vintage: RegulationVintage;
  setVintage: (vintage: RegulationVintage) => void;

  output: SimulationOutput | null;
  simulationError: string | null;
}

const AppStateContext = createContext<AppStateValue | null>(null);

export function AppStateProvider({ children }: { children: ReactNode }) {
  const { engine } = useEngine();
  const [view, setView] = useState<View>("landing");
  const [form, setForm] = useState<FormState>(INITIAL_FORM);
  const [occupancy, setOccupancy] = useState<OccupancyState>(INITIAL_OCCUPANCY);
  const [activeMeasures, setActiveMeasures] = useState<ReadonlySet<MeasureType>>(new Set());
  const [params, setParams] = useState<MeasureParams>(DEFAULT_MEASURE_PARAMS);
  const [vintage, setVintage] = useState<RegulationVintage>("dpe_2021");
  const [output, setOutput] = useState<SimulationOutput | null>(null);
  const [simulationError, setSimulationError] = useState<string | null>(null);

  const updateForm = useCallback((patch: Partial<FormState>) => {
    setForm((prev) => ({ ...prev, ...patch }));
  }, []);

  /** Changing the construction period re-derives the dependent defaults. */
  const setPeriod = useCallback((period: FormState["period"]) => {
    setForm((prev) => ({ ...prev, period, ...defaultsForPeriod(period) }));
  }, []);

  const updateOccupancy = useCallback((patch: Partial<OccupancyState>) => {
    setOccupancy((prev) => ({ ...prev, ...patch }));
  }, []);

  const toggleMeasure = useCallback((type: MeasureType) => {
    setActiveMeasures((prev) => {
      const next = new Set(prev);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      return next;
    });
  }, []);

  const applyBundle = useCallback((measures: MeasureInput[]) => {
    setActiveMeasures(new Set(measures.map((m) => m.type)));
    setParams((prev) => {
      const next = { ...prev };
      for (const m of measures) {
        if (m.type === "wall_insulation" && m.added_r_m2k_per_w != null) {
          next.wallAddedR = m.added_r_m2k_per_w;
        } else if (m.type === "roof_insulation" && m.added_r_m2k_per_w != null) {
          next.roofAddedR = m.added_r_m2k_per_w;
        } else if (m.type === "window_replacement" && m.glazing != null) {
          next.windowGlazing = m.glazing;
        } else if (m.type === "ventilation_upgrade" && m.new_type != null) {
          next.ventilationTarget = m.new_type;
        } else if (
          m.type === "heating_replacement" &&
          m.new_generator != null &&
          (m.new_generator === "heat_pump_air_water" ||
            m.new_generator === "condensing_boiler" ||
            m.new_generator === "wood_pellet_stove")
        ) {
          next.heatingTarget = m.new_generator;
        }
      }
      return next;
    });
  }, []);

  const clearMeasures = useCallback(() => setActiveMeasures(new Set()), []);

  const updateParams = useCallback((patch: Partial<MeasureParams>) => {
    setParams((prev) => ({ ...prev, ...patch }));
  }, []);

  // Run the engine whenever the results are on screen and any input changes.
  const shouldSimulate = view === "results" || view === "scenarios";
  useEffect(() => {
    if (!shouldSimulate || !engine) return;
    try {
      const payload = simulationPayload(form, occupancy, activeMeasures, params, vintage);
      setOutput(engine.runSimulation(payload));
      setSimulationError(null);
    } catch (err) {
      setSimulationError(err instanceof Error ? err.message : String(err));
    }
  }, [shouldSimulate, engine, form, occupancy, activeMeasures, params, vintage]);

  const value = useMemo<AppStateValue>(
    () => ({
      view,
      setView,
      form,
      updateForm,
      setPeriod,
      occupancy,
      updateOccupancy,
      activeMeasures,
      toggleMeasure,
      applyBundle,
      clearMeasures,
      params,
      updateParams,
      vintage,
      setVintage,
      output,
      simulationError,
    }),
    [
      view,
      form,
      updateForm,
      setPeriod,
      occupancy,
      updateOccupancy,
      activeMeasures,
      toggleMeasure,
      applyBundle,
      clearMeasures,
      params,
      updateParams,
      vintage,
      output,
      simulationError,
    ],
  );

  return <AppStateContext.Provider value={value}>{children}</AppStateContext.Provider>;
}

export function useAppState(): AppStateValue {
  const ctx = useContext(AppStateContext);
  if (!ctx) throw new Error("useAppState must be used inside AppStateProvider");
  return ctx;
}
