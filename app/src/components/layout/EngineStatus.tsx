import { AlertTriangle, Check, Loader2 } from "lucide-react";
import { useEngine } from "../../pyodide/PyodideContext";

/** Discreet runtime chip: the Pyodide download happens while the user reads. */
export function EngineStatus() {
  const { status } = useEngine();
  if (status === "loading") {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full bg-cream px-3 py-1 text-xs font-medium text-ink-soft">
        <Loader2 size={13} className="animate-spin" aria-hidden />
        Moteur de calcul en préparation…
      </span>
    );
  }
  if (status === "error") {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full bg-clay-soft px-3 py-1 text-xs font-medium text-clay">
        <AlertTriangle size={13} aria-hidden />
        Moteur indisponible
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-pine-soft px-3 py-1 text-xs font-medium text-pine">
      <Check size={13} aria-hidden />
      Moteur prêt — calcul 100 % local
    </span>
  );
}
