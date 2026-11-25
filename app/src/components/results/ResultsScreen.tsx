import { Suspense, lazy } from "react";
import { motion } from "motion/react";
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  Coins,
  Flame,
  Info,
  Leaf,
  Loader2,
  Pencil,
  Zap,
} from "lucide-react";
import { climateZoneFromPostalCode } from "../../data/climateZones";
import { DWELLING_LABELS, HELP_TEXTS, USE_LABELS } from "../../i18n/fr";
import { useEngine } from "../../pyodide/PyodideContext";
import { useAppState } from "../../state/AppState";
import { HEATING_SYSTEMS } from "../../state/model";
import type { SimulationResult } from "../../types/schema";
import { formatInt } from "../../utils/format";
import { Button } from "../ui/Button";
import { InfoTip } from "../ui/InfoTip";
import { PageActions } from "../ui/PageActions";
import { Segmented, NumberInput } from "../form/fields";
import { DpeBadge, DpeScale } from "./DpeScale";
import { HouseLossMap } from "./HouseLossMap";
import { PrintHypotheses } from "./PrintHypotheses";
import { ProjectsPanel } from "./ProjectsPanel";
import { SummerComfortCard } from "./SummerComfortCard";

// Recharts lives in its own lazy chunk: it is only fetched when a chart is shown.
const LossesChart = lazy(() => import("./LossesChart"));

function StatTile({
  icon,
  label,
  value,
  unit,
  delta,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  unit: string;
  delta?: string;
}) {
  return (
    <div className="rounded-2xl border border-line bg-surface p-4 shadow-card">
      <div className="flex items-center gap-2 text-xs font-medium text-ink-faint">
        {icon}
        {label}
      </div>
      <p className="mt-2">
        <span className="font-display text-2xl font-semibold tabular">{value}</span>
        <span className="ml-1 text-xs text-ink-faint">{unit}</span>
      </p>
      {delta && <p className="mt-0.5 text-xs text-ink-faint">{delta}</p>}
    </div>
  );
}

export function ResultsScreen() {
  const { status, error } = useEngine();
  const {
    form,
    occupancy,
    updateOccupancy,
    output,
    simulationError,
    setView,
    vintage,
    setVintage,
  } = useAppState();

  const zone = climateZoneFromPostalCode(form.postalCode);
  const heatingCarrier = HEATING_SYSTEMS[form.heating].carrier;

  if (status === "error") {
    return (
      <Fallback
        title="Le moteur de calcul n'a pas pu se charger"
        detail={error ?? "Erreur inconnue."}
      />
    );
  }
  if (simulationError) {
    return <Fallback title="La simulation a échoué" detail={simulationError} />;
  }
  if (!output) {
    return (
      <div className="mx-auto flex max-w-2xl flex-col items-center gap-4 px-4 py-28 text-center">
        <Loader2 size={36} className="animate-spin text-pine" aria-hidden />
        <h2 className="font-display text-2xl font-semibold">Préparation du moteur de calcul…</h2>
        <p className="max-w-md text-sm leading-relaxed text-ink-soft">
          RénoSim télécharge son moteur physique (Python via Pyodide) directement dans votre
          navigateur. C'est l'affaire de quelques secondes au premier chargement — vos données ne
          quittent jamais votre appareil.
        </p>
      </div>
    );
  }

  const conventional = output.baseline.conventional;
  const personalized = output.baseline.personalized;
  const isPerso = occupancy.mode === "personalized" && personalized != null;
  const shown: SimulationResult = isPerso ? personalized : conventional;

  return (
    <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.22, 0.65, 0.3, 1] }}
      >
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="font-display text-3xl font-semibold sm:text-4xl">
              Votre situation actuelle
            </h1>
            <p className="mt-1.5 text-sm text-ink-soft">
              {DWELLING_LABELS[form.dwellingType]} de {formatInt(form.livingArea)} m² — zone{" "}
              {zone} —{" "}
              <button
                type="button"
                onClick={() => setView("form")}
                className="inline-flex cursor-pointer items-center gap-1 font-medium text-pine hover:underline print:hidden"
              >
                <Pencil size={13} aria-hidden />
                modifier la description
              </button>
            </p>
          </div>
          <div className="flex items-center gap-2 print:hidden">
            <PageActions />
            <Button size="lg" variant="accent" onClick={() => setView("scenarios")}>
              Explorer les scénarios
              <ArrowRight size={18} aria-hidden />
            </Button>
          </div>
        </div>

        {/* Print-only context line: mode and disclaimer travel with the paper copy. */}
        <p className="mt-2 hidden text-xs leading-relaxed text-ink-soft print:block">
          Simulation RénoSim du {new Date().toLocaleDateString("fr-FR")} — mode{" "}
          {isPerso ? "personnalisé (l'étiquette reste conventionnelle)" : "conventionnel (DPE)"},
          convention {vintage === "dpe_2026" ? "DPE 2026" : "DPE 2021"}. Outil pédagogique — ne
          remplace ni un DPE officiel ni un audit énergétique.
        </p>

        {/* Mode toggle */}
        <div className="mt-8 rounded-3xl border border-line bg-surface p-5 shadow-card print:hidden">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <Segmented
                name="Mode de calcul"
                options={[
                  { value: "conventional", label: "Conventionnel (DPE)" },
                  { value: "personalized", label: "Personnalisé" },
                ]}
                value={occupancy.mode}
                onChange={(mode) => updateOccupancy({ mode })}
              />
              <InfoTip
                text={
                  occupancy.mode === "conventional"
                    ? HELP_TEXTS.conventionalMode
                    : HELP_TEXTS.personalizedMode
                }
              />
            </div>
            <div className="flex items-center gap-2 text-xs text-ink-faint">
              Convention énergie primaire :
              <Segmented
                name="Convention DPE"
                options={[
                  { value: "dpe_2021", label: "DPE 2021" },
                  { value: "dpe_2026", label: "DPE 2026" },
                ]}
                value={vintage}
                onChange={setVintage}
              />
              <InfoTip text="Depuis le 1er janvier 2026, le coefficient d'énergie primaire de l'électricité passe de 2,3 à 1,9 (arrêté du 13 août 2025). « DPE 2021 » correspond aux diagnostics émis entre 2021 et 2025." />
            </div>
          </div>

          {occupancy.mode === "personalized" && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              className="overflow-hidden"
            >
              <div className="mt-4 grid gap-5 border-t border-line pt-4 sm:grid-cols-2 lg:grid-cols-4">
                <label className="space-y-1.5 text-sm">
                  <span className="font-medium">Température de consigne</span>
                  <div className="flex items-center gap-3">
                    <input
                      type="range"
                      min={16}
                      max={23}
                      step={0.5}
                      value={occupancy.setpointC}
                      onChange={(e) => updateOccupancy({ setpointC: Number(e.target.value) })}
                      className="w-full accent-(--color-pine)"
                    />
                    <span className="w-14 text-right font-semibold tabular">
                      {occupancy.setpointC.toLocaleString("fr-FR")} °C
                    </span>
                  </div>
                </label>
                <label className="space-y-1.5 text-sm">
                  <span className="font-medium">Occupants</span>
                  <div>
                    <NumberInput
                      value={occupancy.occupants}
                      onChange={(v) =>
                        updateOccupancy({ occupants: Math.min(10, Math.max(1, Math.round(v))) })
                      }
                      min={1}
                      max={10}
                      ariaLabel="Nombre d'occupants"
                    />
                  </div>
                </label>
                <label className="space-y-1.5 text-sm">
                  <span className="font-medium">Prix électricité</span>
                  <div>
                    <NumberInput
                      value={occupancy.electricityPrice ?? 0.2516}
                      onChange={(v) => updateOccupancy({ electricityPrice: v })}
                      min={0.05}
                      max={1}
                      step={0.001}
                      suffix="€/kWh"
                      ariaLabel="Prix de l'électricité en euros par kilowattheure"
                    />
                  </div>
                </label>
                {heatingCarrier !== "electricity" && (
                  <label className="space-y-1.5 text-sm">
                    <span className="font-medium">Prix énergie de chauffage</span>
                    <div>
                      <NumberInput
                        value={occupancy.heatingCarrierPrice ?? 0.1}
                        onChange={(v) => updateOccupancy({ heatingCarrierPrice: v })}
                        min={0.02}
                        max={1}
                        step={0.001}
                        suffix="€/kWh"
                        ariaLabel="Prix de l'énergie de chauffage en euros par kilowattheure"
                      />
                    </div>
                  </label>
                )}
              </div>
              <p className="mt-4 flex items-start gap-2 rounded-xl bg-amber-soft px-4 py-3 text-xs leading-relaxed text-ink-soft">
                <Info size={14} className="mt-0.5 shrink-0 text-amber-deep" aria-hidden />
                Les consommations, coûts et émissions ci-dessous reflètent VOS habitudes.
                L'étiquette DPE, elle, reste calculée avec le scénario conventionnel : c'est la
                règle du diagnostic, elle ne bouge pas.
              </p>
            </motion.div>
          )}
        </div>

        {/* Label + stats */}
        <div className="mt-6 grid gap-6 lg:grid-cols-[1.1fr_1fr]">
          <section
            aria-label="Étiquette DPE estimée"
            className="rounded-3xl border border-line bg-surface p-6 shadow-card sm:p-8"
          >
            <div className="mb-5 flex items-center justify-between">
              <h2 className="font-display text-xl font-semibold">Étiquette DPE estimée</h2>
              <InfoTip text="Étiquette au double seuil du DPE 2021 : la plus défavorable des classes énergie (kWhep/m²/an) et climat (kgCO₂/m²/an). Estimation pédagogique — seul un diagnostiqueur certifié peut établir un DPE opposable." />
            </div>
            {conventional.label && (
              <DpeScale
                label={conventional.label}
                cepKwhepM2={conventional.primary_energy_kwh_m2}
                gesKgM2={conventional.co2_kg_m2}
              />
            )}
            <div className="mt-5 flex flex-wrap gap-2 text-xs">
              {conventional.energy_class && (
                <span className="inline-flex items-center gap-1.5 rounded-full bg-cream px-3 py-1.5 font-medium text-ink-soft">
                  Énergie : classe {conventional.energy_class} —{" "}
                  {formatInt(conventional.primary_energy_kwh_m2)} kWhep/m²·an
                </span>
              )}
              {conventional.climate_class && (
                <span className="inline-flex items-center gap-1.5 rounded-full bg-cream px-3 py-1.5 font-medium text-ink-soft">
                  Climat : classe {conventional.climate_class} — {formatInt(conventional.co2_kg_m2)}{" "}
                  kgCO₂/m²·an
                </span>
              )}
            </div>
          </section>

          <section aria-label="Chiffres clés" className="flex flex-col gap-4">
            <div className="grid grid-cols-2 gap-4">
              <StatTile
                icon={<Zap size={14} aria-hidden />}
                label="Énergie finale"
                value={formatInt(shown.final_energy_kwh_m2)}
                unit="kWh/m²·an"
              />
              <StatTile
                icon={<Flame size={14} aria-hidden />}
                label="Énergie primaire"
                value={formatInt(shown.primary_energy_kwh_m2)}
                unit="kWhep/m²·an"
              />
              <StatTile
                icon={<Coins size={14} aria-hidden />}
                label="Facture énergie estimée"
                value={formatInt(shown.annual_cost_eur)}
                unit="€/an"
              />
              <StatTile
                icon={<Leaf size={14} aria-hidden />}
                label="Émissions"
                value={formatInt(shown.co2_kg_m2 * form.livingArea)}
                unit="kgCO₂/an"
              />
            </div>
            <div className="rounded-2xl border border-line bg-surface p-5 shadow-card">
              <h3 className="text-sm font-semibold">Répartition par usage</h3>
              <ul className="mt-3 space-y-2.5">
                {Object.entries(shown.final_energy_kwh_by_use)
                  .filter(([, kwh]) => kwh > 0)
                  .map(([use, kwh]) => {
                  const total = Object.values(shown.final_energy_kwh_by_use).reduce(
                    (a, b) => a + b,
                    0,
                  );
                  const share = total > 0 ? (kwh / total) * 100 : 0;
                  return (
                    <li key={use} className="text-xs">
                      <div className="flex justify-between font-medium">
                        <span>{USE_LABELS[use] ?? use}</span>
                        <span className="tabular text-ink-soft">
                          {formatInt(kwh)} kWh · {share.toFixed(0)} %
                        </span>
                      </div>
                      <div className="mt-1 h-2 overflow-hidden rounded-full bg-cream">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${share}%` }}
                          transition={{ duration: 0.7, ease: "easeOut" }}
                          className="h-full rounded-full bg-pine"
                        />
                      </div>
                    </li>
                  );
                })}
              </ul>
            </div>
          </section>
        </div>

        {/* Passive summer comfort (#16): shown beside the winter label, never merged. */}
        <SummerComfortCard summer={output.summer_comfort} />

        {conventional.label && <PassoireAlert label={conventional.label} />}

        {/* Losses */}
        <section
          aria-label="Par où part la chaleur"
          className="mt-6 rounded-3xl border border-line bg-surface p-6 shadow-card sm:p-8"
        >
          <div className="mb-2 flex items-center justify-between">
            <h2 className="font-display text-xl font-semibold">Par où part la chaleur ?</h2>
            <InfoTip text="Part de chaque poste dans le coefficient de déperditions GV (W/K) : parois, ponts thermiques, renouvellement d'air. C'est la carte des priorités de rénovation." />
          </div>
          <p className="mb-4 text-sm text-ink-soft">
            Déperditions totales : {formatInt(shown.envelope.total_w_per_k)} W/K. Les postes les
            plus hauts sont vos gisements d'économies prioritaires.
          </p>
          <div className="grid items-center gap-8 lg:grid-cols-2">
            <HouseLossMap envelope={shown.envelope} />
            <Suspense
              fallback={
                <div className="flex h-64 items-center justify-center text-sm text-ink-faint">
                  Chargement du graphique…
                </div>
              }
            >
              <LossesChart envelope={shown.envelope} />
            </Suspense>
          </div>
        </section>

        {/* Multi-project save & compare (#12) */}
        <ProjectsPanel />

        {/* Printed / PDF report: the inputs travel with the outputs (#11). */}
        <PrintHypotheses form={form} />

        <div className="mt-8 flex items-center justify-between print:hidden">
          <Button variant="ghost" onClick={() => setView("form")}>
            <ArrowLeft size={16} aria-hidden />
            Modifier ma description
          </Button>
          <Button size="lg" onClick={() => setView("scenarios")}>
            Explorer les scénarios de rénovation
            <ArrowRight size={18} aria-hidden />
          </Button>
        </div>
      </motion.div>
    </div>
  );
}

/**
 * Rental-ban calendar of the loi Climat & Résilience (art. L173-2 CCH). Purely
 * informative; no financial-aid computation (out of scope). Only E/F/G are
 * concerned. Sourced: service-public.fr / loi n°2021-1104.
 */
const RENTAL_BAN: Record<"E" | "F" | "G", { passoire: boolean; text: string }> = {
  G: {
    passoire: true,
    text: "Depuis le 1er janvier 2025, les logements classés G ne peuvent plus être proposés à la location (nouvelles mises en location et renouvellements de bail).",
  },
  F: {
    passoire: true,
    text: "À partir du 1er janvier 2028, les logements classés F ne pourront plus être proposés à la location.",
  },
  E: {
    passoire: false,
    text: "À partir du 1er janvier 2034, les logements classés E ne pourront plus être proposés à la location.",
  },
};

function PassoireAlert({ label }: { label: string }) {
  const entry = RENTAL_BAN[label as "E" | "F" | "G"];
  if (!entry) return null;
  return (
    <section
      aria-label="Alerte réglementaire location"
      className="mt-6 flex items-start gap-3 rounded-3xl border border-clay/30 bg-clay-soft px-5 py-4 sm:px-6"
    >
      <AlertTriangle size={20} className="mt-0.5 shrink-0 text-clay" aria-hidden />
      <div className="text-sm leading-relaxed text-ink">
        <p className="font-semibold">
          {entry.passoire
            ? `Logement classé ${label} : passoire énergétique`
            : `Logement classé ${label} : bientôt concerné par l'interdiction de location`}
        </p>
        <p className="mt-1 text-ink-soft">
          {entry.text} Ce calendrier de la loi Climat &amp; Résilience concerne la location ; il
          ne s'applique pas aux logements occupés par leur propriétaire.{" "}
          <a
            href="https://france-renov.gouv.fr"
            target="_blank"
            rel="noreferrer"
            className="font-medium text-pine hover:underline"
          >
            Conseils et parcours de rénovation sur France Rénov'
          </a>
          .
        </p>
      </div>
    </section>
  );
}

function Fallback({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="mx-auto flex max-w-xl flex-col items-center gap-4 px-4 py-28 text-center">
      <span className="flex h-14 w-14 items-center justify-center rounded-full bg-clay-soft text-clay">
        <AlertTriangle size={26} aria-hidden />
      </span>
      <h2 className="font-display text-2xl font-semibold">{title}</h2>
      <p className="text-sm leading-relaxed text-ink-soft">{detail}</p>
      <p className="text-sm text-ink-soft">
        Réessayez en rechargeant la page. Si le problème persiste, signalez-le sur{" "}
        <a
          href="https://github.com/quetinn/renosim/issues"
          target="_blank"
          rel="noreferrer"
          className="font-medium text-pine hover:underline"
        >
          le dépôt du projet
        </a>
        .
      </p>
    </div>
  );
}

export { DpeBadge };
