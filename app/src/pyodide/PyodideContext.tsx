import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { loadEngine, type EngineHandle } from "./loader";

export type EngineStatus = "loading" | "ready" | "error";

interface EngineContextValue {
  status: EngineStatus;
  engine: EngineHandle | null;
  error: string | null;
}

const EngineContext = createContext<EngineContextValue>({
  status: "loading",
  engine: null,
  error: null,
});

/**
 * Starts loading Pyodide as soon as the app mounts, so the ~10 s download
 * happens while the visitor reads the landing page and fills the form.
 */
export function PyodideProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<EngineStatus>("loading");
  const [engine, setEngine] = useState<EngineHandle | null>(null);
  const [error, setError] = useState<string | null>(null);
  const startedRef = useRef(false);

  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;
    loadEngine()
      .then((handle) => {
        setEngine(handle);
        setStatus("ready");
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : String(err));
        setStatus("error");
      });
  }, []);

  return (
    <EngineContext.Provider value={{ status, engine, error }}>{children}</EngineContext.Provider>
  );
}

export function useEngine(): EngineContextValue {
  return useContext(EngineContext);
}
