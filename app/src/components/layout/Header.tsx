import { BookOpen, Leaf } from "lucide-react";
import { useAppState } from "../../state/AppState";
import { Button } from "../ui/Button";

export function Header({ onOpenMethod }: { onOpenMethod: () => void }) {
  const { view, setView } = useAppState();
  return (
    <header className="sticky top-0 z-40 border-b border-line/70 bg-paper/85 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-3 px-4 sm:px-6">
        <button
          type="button"
          onClick={() => setView("landing")}
          className="flex cursor-pointer items-center gap-2.5"
          aria-label="RénoSim — retour à l'accueil"
        >
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-pine text-white">
            <Leaf size={18} aria-hidden />
          </span>
          <span className="font-display text-xl font-semibold tracking-tight">RénoSim</span>
        </button>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onOpenMethod}
            className="inline-flex min-h-11 cursor-pointer items-center gap-1.5 rounded-full px-3 text-sm font-medium text-ink-soft transition-colors hover:text-pine"
          >
            <BookOpen size={16} aria-hidden />
            <span className="hidden sm:inline">Comment est-ce calculé ?</span>
            <span className="sm:hidden">Méthode</span>
          </button>
          {view === "landing" && (
            <Button onClick={() => setView("form")}>Simuler mon logement</Button>
          )}
        </div>
      </div>
    </header>
  );
}
