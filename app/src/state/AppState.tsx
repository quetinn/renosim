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
  DpeClass,
  MeasureInput,
  MeasureType,
  SimulationOutput,
  VintageChoice,
} from "../types/schema";
import {
  DEFAULT_MEASURE_PARAMS,
  EMPTY_GEOMETRY,
  INITIAL_FORM,
  INITIAL_OCCUPANCY,
  defaultsForPeriod,
  simulationPayload,
  type FormState,
  type MeasureParams,
  type OccupancyState,
} from "./model";

export type View = "landing" | "form" | "results" | "scenarios";

// ── Local persistence (the data never leaves the browser) ────────────────────

const STORAGE_KEY = "renosim:v1";

interface PersistedState {
  form: FormState;
  occupancy: OccupancyState;
  params: MeasureParams;
  activeMeasures: MeasureType[];
  vintage: VintageChoice;
}

/** Fill defaults on a raw snapshot (localStorage or shared URL); null if unusable. */
function sanitizePersisted(data: Partial<PersistedState> | null): PersistedState | null {
  if (!data || typeof data !== "object" || !data.form) return null;
  return {
    form: {
      ...INITIAL_FORM,
      ...data.form,
      geometry: { ...EMPTY_GEOMETRY, ...(data.form.geometry ?? {}) },
    },
    occupancy: { ...INITIAL_OCCUPANCY, ...(data.occupancy ?? {}) },
    params: { ...DEFAULT_MEASURE_PARAMS, ...(data.params ?? {}) },
    activeMeasures: Array.isArray(data.activeMeasures) ? data.activeMeasures : [],
    vintage:
      data.vintage === "dpe_2021" || data.vintage === "dpe_2026" || data.vintage === "dpe_2027"
        ? data.vintage
        : "current",
  };
}

/** Restore a previous session; unknown/missing fields fall back to defaults. */
function loadPersisted(): PersistedState | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return sanitizePersisted(JSON.parse(raw) as Partial<PersistedState> | null);
  } catch {
    return null; // corrupted storage or private mode: start fresh
  }
}

// ── Share-by-URL (#7): the whole description travels in the fragment, which is
// never sent to any server — consistent with "vos données restent chez vous".
const SHARE_HASH_PREFIX = "#s=";

function encodeShareState(state: PersistedState): string {
  const bytes = new TextEncoder().encode(JSON.stringify(state));
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  // URL-safe base64 so the link survives messaging apps unescaped.
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

/** Parse a shared URL fragment; the hash is cleared after a successful import. */
function loadShared(): PersistedState | null {
  if (!window.location.hash.startsWith(SHARE_HASH_PREFIX)) return null;
  try {
    const encoded = window.location.hash
      .slice(SHARE_HASH_PREFIX.length)
      .replace(/-/g, "+")
      .replace(/_/g, "/");
    const binary = atob(encoded);
    const bytes = Uint8Array.from(binary, (c) => c.charCodeAt(0));
    const state = sanitizePersisted(
      JSON.parse(new TextDecoder().decode(bytes)) as Partial<PersistedState> | null,
    );
    if (state) {
      history.replaceState(null, "", window.location.pathname + window.location.search);
    }
    return state;
  } catch {
    return null; // malformed link: fall back to the local session
  }
}

const SHARED = loadShared();
const PERSISTED = SHARED ?? loadPersisted();

// ── Multi-project store (#12): named snapshots to compare several homes. ─────

const PROJECTS_KEY = "renosim:projects:v1";

/** Conventional-baseline summary captured at save time, for the comparison table. */
export interface ProjectSummary {
  label: DpeClass | null;
  primary_energy_kwh_m2: number;
  annual_cost_eur: number;
  co2_kg_m2: number;
}

export interface SavedProject {
  id: string;
  name: string;
  savedAt: string; // ISO date
  state: PersistedState;
  summary: ProjectSummary | null;
}

function loadProjects(): SavedProject[] {
  try {
    const raw = localStorage.getItem(PROJECTS_KEY);
    if (!raw) return [];
    const data = JSON.parse(raw) as unknown;
    if (!Array.isArray(data)) return [];
    return data.flatMap((item: Partial<SavedProject>) => {
      const state = sanitizePersisted(item?.state ?? null);
      if (!state || typeof item.id !== "string" || typeof item.name !== "string") return [];
      return [
        {
          id: item.id,
          name: item.name,
          savedAt: typeof item.savedAt === "string" ? item.savedAt : new Date().toISOString(),
          state,
          summary: item.summary ?? null,
        },
      ];
    });
  } catch {
    return [];
  }
}

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

  vintage: VintageChoice;
  setVintage: (vintage: VintageChoice) => void;

  /** Shareable link embedding the current description in the URL fragment. */
  shareUrl: () => string;

  /** Named home snapshots ("multi-projets") with their saved summaries. */
  projects: SavedProject[];
  saveProject: (name: string) => void;
  loadProject: (id: string) => void;
  deleteProject: (id: string) => void;

  /** Clears the locally saved session and restores every default. */
  resetAll: () => void;

  output: SimulationOutput | null;
  simulationError: string | null;
}

const AppStateContext = createContext<AppStateValue | null>(null);

export function AppStateProvider({ children }: { children: ReactNode }) {
  const { engine } = useEngine();
  // A shared link lands straight on the results of the imported simulation.
  const [view, setView] = useState<View>(SHARED ? "results" : "landing");
  const [form, setForm] = useState<FormState>(PERSISTED?.form ?? INITIAL_FORM);
  const [occupancy, setOccupancy] = useState<OccupancyState>(
    PERSISTED?.occupancy ?? INITIAL_OCCUPANCY,
  );
  const [activeMeasures, setActiveMeasures] = useState<ReadonlySet<MeasureType>>(
    new Set(PERSISTED?.activeMeasures ?? []),
  );
  const [params, setParams] = useState<MeasureParams>(PERSISTED?.params ?? DEFAULT_MEASURE_PARAMS);
  const [vintage, setVintage] = useState<VintageChoice>(PERSISTED?.vintage ?? "current");
  const [output, setOutput] = useState<SimulationOutput | null>(null);
  const [simulationError, setSimulationError] = useState<string | null>(null);

  // Persist the description locally so a reload does not lose the form
  // ("vos données restent chez vous" — nothing is sent anywhere).
  useEffect(() => {
    try {
      const snapshot: PersistedState = {
        form,
        occupancy,
        params,
        activeMeasures: [...activeMeasures],
        vintage,
      };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(snapshot));
    } catch {
      // Storage full or blocked (private mode): persistence is best-effort.
    }
  }, [form, occupancy, params, activeMeasures, vintage]);

  /** Clear the saved session and restore every default. */
  const resetAll = useCallback(() => {
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      // ignore
    }
    setForm(INITIAL_FORM);
    setOccupancy(INITIAL_OCCUPANCY);
    setActiveMeasures(new Set());
    setParams(DEFAULT_MEASURE_PARAMS);
    setVintage("current");
    setOutput(null);
    setSimulationError(null);
  }, []);

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
      // Insulation measures keep the current material/thickness params: the
      // bundle defaults (added R 7 / 3.7) match the default glass-wool params.
      for (const m of measures) {
        if (m.type === "window_replacement" && m.glazing != null) {
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

  // ── Multi-project store (#12) ──────────────────────────────────────────────
  const [projects, setProjects] = useState<SavedProject[]>(loadProjects);

  useEffect(() => {
    try {
      localStorage.setItem(PROJECTS_KEY, JSON.stringify(projects));
    } catch {
      // best-effort, as for the session snapshot
    }
  }, [projects]);

  const saveProject = useCallback(
    (name: string) => {
      const conventional = output?.baseline.conventional;
      const project: SavedProject = {
        id:
          typeof crypto !== "undefined" && "randomUUID" in crypto
            ? crypto.randomUUID()
            : String(Date.now()),
        name: name.trim() || "Sans nom",
        savedAt: new Date().toISOString(),
        state: { form, occupancy, params, activeMeasures: [...activeMeasures], vintage },
        summary: conventional
          ? {
              label: conventional.label,
              primary_energy_kwh_m2: conventional.primary_energy_kwh_m2,
              annual_cost_eur: conventional.annual_cost_eur,
              co2_kg_m2: conventional.co2_kg_m2,
            }
          : null,
      };
      setProjects((prev) => [...prev, project]);
    },
    [form, occupancy, params, activeMeasures, vintage, output],
  );

  const loadProject = useCallback(
    (id: string) => {
      const project = projects.find((p) => p.id === id);
      if (!project) return;
      setForm(project.state.form);
      setOccupancy(project.state.occupancy);
      setParams(project.state.params);
      setActiveMeasures(new Set(project.state.activeMeasures));
      setVintage(project.state.vintage);
    },
    [projects],
  );

  const deleteProject = useCallback((id: string) => {
    setProjects((prev) => prev.filter((p) => p.id !== id));
  }, []);

  const shareUrl = useCallback(() => {
    const snapshot: PersistedState = {
      form,
      occupancy,
      params,
      activeMeasures: [...activeMeasures],
      vintage,
    };
    const base = window.location.origin + window.location.pathname + window.location.search;
    return base + SHARE_HASH_PREFIX + encodeShareState(snapshot);
  }, [form, occupancy, params, activeMeasures, vintage]);

  // Run the engine (async, in its Web Worker) whenever the results are on
  // screen and any input changes; stale responses are dropped on cleanup.
  // The label-target search (63 combinations) is only requested where it is
  // displayed, to keep the results screen updates instant.
  const shouldSimulate = view === "results" || view === "scenarios";
  const wantLabelTargets = view === "scenarios";
  useEffect(() => {
    if (!shouldSimulate || !engine) return;
    let cancelled = false;
    try {
      const payload = simulationPayload(
        form,
        occupancy,
        activeMeasures,
        params,
        vintage,
        wantLabelTargets,
      );
      engine
        .runSimulation(payload)
        .then((result) => {
          if (cancelled) return;
          setOutput(result);
          setSimulationError(null);
        })
        .catch((err: unknown) => {
          if (cancelled) return;
          setSimulationError(err instanceof Error ? err.message : String(err));
        });
    } catch (err) {
      setSimulationError(err instanceof Error ? err.message : String(err));
    }
    return () => {
      cancelled = true;
    };
  }, [shouldSimulate, wantLabelTargets, engine, form, occupancy, activeMeasures, params, vintage]);

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
      shareUrl,
      projects,
      saveProject,
      loadProject,
      deleteProject,
      resetAll,
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
      shareUrl,
      projects,
      saveProject,
      loadProject,
      deleteProject,
      resetAll,
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
