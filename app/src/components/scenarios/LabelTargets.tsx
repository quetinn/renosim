import { Loader2, Target } from "lucide-react";
import { useState } from "react";
import { MEASURE_LABELS } from "../../i18n/fr";
import type { DpeClass, LabelTargetEntry, MeasureInput, MeasureType } from "../../types/schema";
import { formatEuroRange, formatEuros, formatInt, formatPayback } from "../../utils/format";
import { Button } from "../ui/Button";
import { InfoTip } from "../ui/InfoTip";
import { DpeBadge } from "../results/DpeScale";

const CLASSES: DpeClass[] = ["A", "B", "C", "D", "E", "F", "G"];

/**
 * "Que faut-il pour atteindre C ?" — the engine evaluates the 63 combinations
 * of the six measures and returns the cheapest one reaching each class better
 * than the baseline (backlog #8). Conventional mode by construction: the DPE
 * label is regulatory.
 */
export function LabelTargets({
  baselineLabel,
  targets,
  onApply,
}: {
  baselineLabel: DpeClass;
  targets: Partial<Record<DpeClass, LabelTargetEntry>> | null;
  onApply: (measures: MeasureInput[]) => void;
}) {
  const [picked, setPicked] = useState<DpeClass | null>(null);

  // Candidate targets, closest to the baseline first (E, D, C… for an F house).
  const candidates = CLASSES.slice(0, CLASSES.indexOf(baselineLabel)).reverse();
  if (candidates.length === 0) return null; // already class A

  // Default selection: class C (the pedagogical milestone), else the most
  // ambitious reachable class.
  const reachable = candidates.filter((c) => targets?.[c] != null);
  const selected =
    picked && targets?.[picked] != null
      ? picked
      : reachable.includes("C")
        ? "C"
        : (reachable.at(-1) ?? null);
  const entry = selected ? targets?.[selected] : undefined;

  return (
    <section
      aria-label="Objectif d'étiquette"
      className="mt-10 rounded-3xl border border-line bg-surface p-6 shadow-card sm:p-8"
    >
      <div className="flex items-center gap-2">
        <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-pine-soft text-pine">
          <Target size={18} aria-hidden />
        </span>
        <h2 className="font-display text-2xl font-semibold">Viser une étiquette</h2>
        <InfoTip text="Le moteur compare les 63 combinaisons possibles des six gestes (avec les paramètres choisis sur les cartes) et retient la moins chère qui atteint la classe visée. Calcul conventionnel : c'est la règle de l'étiquette DPE." />
      </div>
      <p className="mt-1.5 text-sm leading-relaxed text-ink-soft">
        Quelle combinaison de gestes, la moins chère possible, fait passer votre maison de{" "}
        <DpeBadge label={baselineLabel} /> à la classe visée ?
      </p>

      {targets === null ? (
        <p className="mt-5 flex items-center gap-2 text-sm text-ink-faint">
          <Loader2 size={16} className="animate-spin" aria-hidden />
          Recherche des combinaisons les moins chères…
        </p>
      ) : (
        <>
          <div className="mt-5 flex flex-wrap gap-2" role="group" aria-label="Classe visée">
            {candidates.map((cls) => {
              const available = targets[cls] != null;
              const active = cls === selected;
              return (
                <button
                  key={cls}
                  type="button"
                  disabled={!available}
                  aria-pressed={active}
                  title={
                    available
                      ? `Voir le bouquet le moins cher pour atteindre ${cls}`
                      : `La classe ${cls} est hors de portée des six gestes`
                  }
                  onClick={() => setPicked(cls)}
                  className={`min-h-11 cursor-pointer rounded-full border px-4 py-1.5 text-sm font-semibold transition-all disabled:cursor-not-allowed disabled:opacity-35 ${
                    active
                      ? "border-pine bg-pine text-on-pine"
                      : "border-line-strong bg-surface text-ink hover:border-pine"
                  }`}
                >
                  Atteindre {cls}
                </button>
              );
            })}
          </div>

          {reachable.length === 0 && (
            <p className="mt-4 text-sm leading-relaxed text-ink-soft">
              Même les six gestes combinés ne suffisent pas à gagner une classe sur cette maison —
              un audit énergétique approfondi (au-delà des gestes couverts en V1) est recommandé.
            </p>
          )}

          {entry && selected && (
            <div className="mt-5 rounded-2xl border border-pine/25 bg-pine-mist p-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex flex-wrap items-center gap-2">
                  {entry.measures.map((m) => (
                    <span
                      key={m.type}
                      className="rounded-full bg-surface px-3 py-1 text-xs font-semibold text-pine-deep"
                    >
                      {MEASURE_LABELS[m.type as MeasureType].title}
                    </span>
                  ))}
                </div>
                <Button onClick={() => onApply(entry.measures)} className="print:hidden">
                  Activer ce bouquet
                </Button>
              </div>
              <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-4">
                <div>
                  <dt className="text-xs font-medium text-ink-faint">Travaux (fourchette)</dt>
                  <dd className="mt-0.5 font-semibold tabular">
                    {formatEuroRange(entry.investment_low_eur, entry.investment_high_eur)}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-medium text-ink-faint">Économies</dt>
                  <dd className="mt-0.5 font-semibold text-pine tabular">
                    {formatEuros(entry.annual_savings_eur)}/an
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-medium text-ink-faint">Retour simple</dt>
                  <dd className="mt-0.5 font-semibold tabular">
                    {entry.payback_years_low === null
                      ? "> 30 ans"
                      : `${formatPayback(entry.payback_years_low)} – ${formatPayback(entry.payback_years_high)}`}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-medium text-ink-faint">Étiquette atteinte</dt>
                  <dd className="mt-0.5 flex items-center gap-2">
                    <DpeBadge label={entry.after_label} />
                    <span className="text-xs text-ink-soft tabular">
                      {formatInt(entry.after_primary_energy_kwh_m2)} kWhep/m²·an
                    </span>
                  </dd>
                </div>
              </dl>
            </div>
          )}
        </>
      )}
    </section>
  );
}
