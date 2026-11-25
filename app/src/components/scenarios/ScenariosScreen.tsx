import { motion } from "motion/react";
import {
  ArrowLeft,
  ArrowRight,
  BrickWall,
  Check,
  Droplets,
  Fan,
  Flame,
  Blinds,
  Home,
  Info,
  Leaf,
  Lightbulb,
  Loader2,
  PiggyBank,
  Sun,
} from "lucide-react";
import { Suspense, lazy, type ReactNode } from "react";
import { INSULATION_MATERIAL_ORDER, addedRPreview } from "../../data/insulationMaterials";
import {
  BUNDLE_LABELS,
  GLAZING_LABELS,
  INSULATION_MATERIAL_LABELS,
  MEASURE_LABELS,
  SUMMER_COMFORT_LEVEL_LABELS,
  VENTILATION_LABELS,
} from "../../i18n/fr";
import { useEngine } from "../../pyodide/PyodideContext";
import { useAppState } from "../../state/AppState";
import type {
  InsulationMaterial,
  MeasurePreview,
  MeasureType,
  ScenarioOutput,
  SummerComfortLevel,
} from "../../types/schema";
import {
  formatEuroRange,
  formatEuros,
  formatInt,
  formatKgCo2,
  formatMonth,
  formatPayback,
} from "../../utils/format";
import { Button } from "../ui/Button";
import { InfoTip } from "../ui/InfoTip";
import { PageActions } from "../ui/PageActions";
import { DpeBadge } from "../results/DpeScale";
import { LabelTargets } from "./LabelTargets";

const MEASURE_ICONS: Record<MeasureType, ReactNode> = {
  roof_insulation: <Home size={20} aria-hidden />,
  wall_insulation: <BrickWall size={20} aria-hidden />,
  window_replacement: <Blinds size={20} aria-hidden />,
  heating_replacement: <Flame size={20} aria-hidden />,
  dhw_upgrade: <Droplets size={20} aria-hidden />,
  ventilation_upgrade: <Fan size={20} aria-hidden />,
  solar_protection_installation: <Sun size={20} aria-hidden />,
};

const CARD_ORDER: MeasureType[] = [
  "roof_insulation",
  "wall_insulation",
  "window_replacement",
  "heating_replacement",
  "dhw_upgrade",
  "ventilation_upgrade",
  "solar_protection_installation",
];

function scenarioTitle(id: string): string {
  if (id === "bouquet") return "Votre bouquet";
  return MEASURE_LABELS[id as MeasureType]?.title ?? id;
}

/** Compact names for the chart labels, where the full titles overlap. */
const SHORT_TITLES: Record<string, string> = {
  roof_insulation: "Combles",
  wall_insulation: "Murs",
  window_replacement: "Fenêtres",
  heating_replacement: "Chauffage",
  dhw_upgrade: "Eau chaude",
  ventilation_upgrade: "VMC",
  solar_protection_installation: "Volets/BSO",
  bouquet: "Votre bouquet",
};

/** Ordre des niveaux de confort d'été pour comparer avant/après. */
const SUMMER_LEVEL_ORDER: SummerComfortLevel[] = ["insufficient", "medium", "good"];

const SUMMER_LEVEL_CLASS: Record<SummerComfortLevel, string> = {
  insufficient: "text-clay",
  medium: "text-amber-deep",
  good: "text-pine",
};

/** Compact « Moyen → Bon » cell; a dash when the scenario changes nothing. */
function SummerDelta({
  before,
  after,
}: {
  before: SummerComfortLevel;
  after: SummerComfortLevel;
}) {
  if (before === after) {
    return <span className="text-ink-faint">—</span>;
  }
  return (
    <span className="inline-flex items-center gap-1 whitespace-nowrap">
      <span className={SUMMER_LEVEL_CLASS[before]}>{SUMMER_COMFORT_LEVEL_LABELS[before]}</span>
      <ArrowRight size={11} className="text-ink-faint" aria-hidden />
      <span className={`font-semibold ${SUMMER_LEVEL_CLASS[after]}`}>
        {SUMMER_COMFORT_LEVEL_LABELS[after]}
      </span>
    </span>
  );
}

const selectClass =
  "mt-2 w-full cursor-pointer rounded-xl border border-line bg-surface px-3 py-2 text-xs font-medium text-ink outline-none focus:border-pine";

// Recharts lives in its own lazy chunk: it is only fetched when a chart is shown.
const CostGainChart = lazy(() => import("./CostGainChart"));

export function ScenariosScreen() {
  const { status } = useEngine();
  const {
    output,
    activeMeasures,
    toggleMeasure,
    applyBundle,
    clearMeasures,
    params,
    updateParams,
    occupancy,
    form,
    setView,
    simulationError,
  } = useAppState();

  if (!output || status !== "ready") {
    return (
      <div className="mx-auto flex max-w-xl flex-col items-center gap-4 px-4 py-28 text-center">
        <Loader2 size={32} className="animate-spin text-pine" aria-hidden />
        <p className="text-sm text-ink-soft">
          {simulationError ?? "Chargement du moteur de calcul…"}
        </p>
      </div>
    );
  }

  const isPerso = occupancy.mode === "personalized";
  const baseline = output.baseline.conventional;
  const scenarios = output.scenarios;
  const bouquet = scenarios.find((s) => s.id === "bouquet");
  const singles = scenarios.filter((s) => s.id !== "bouquet");
  const sumSingleSavings = singles.reduce(
    (acc, s) => acc + assessment(s, isPerso).annual_savings_eur,
    0,
  );

  // "Par où commencer" — rank the single-measure previews (conventional):
  // most profitable = lowest positive payback; biggest CO2 gain = highest ΔCO2.
  const badges = pickMeasureBadges(output.measure_previews);
  const summerBefore = output.summer_comfort.level;
  const improvesSummer = (type: MeasureType) =>
    SUMMER_LEVEL_ORDER.indexOf(output.measure_previews[type].summer_comfort_level_after) >
    SUMMER_LEVEL_ORDER.indexOf(summerBefore);

  return (
    <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.22, 0.65, 0.3, 1] }}
      >
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="font-display text-3xl font-semibold sm:text-4xl">Mes scénarios</h1>
            <p className="mt-1.5 max-w-2xl text-sm leading-relaxed text-ink-soft">
              Activez des gestes un par un, ou partez d'un bouquet type. Situation de départ :
              étiquette{" "}
              {baseline.label && <DpeBadge label={baseline.label} />} —{" "}
              {formatInt(baseline.primary_energy_kwh_m2)} kWhep/m²·an.
            </p>
          </div>
          <div className="flex items-center gap-1 print:hidden">
            <PageActions />
            <Button variant="ghost" onClick={() => setView("results")}>
              <ArrowLeft size={16} aria-hidden />
              Ma situation
            </Button>
          </div>
        </div>

        {/* Predefined bundles */}
        <div
          className="mt-7 flex flex-wrap gap-2.5 print:hidden"
          role="group"
          aria-label="Bouquets prédéfinis"
        >
          {Object.entries(output.bundles).map(([key, measures]) => {
            const label = BUNDLE_LABELS[key];
            if (!label) return null;
            return (
              <button
                key={key}
                type="button"
                onClick={() => applyBundle(measures)}
                title={label.description}
                className="min-h-11 cursor-pointer rounded-full border border-pine/40 bg-pine-mist px-5 py-2 text-sm font-semibold text-pine-deep transition-all hover:border-pine hover:bg-pine-soft"
              >
                {label.title}
              </button>
            );
          })}
          {activeMeasures.size > 0 && (
            <button
              type="button"
              onClick={clearMeasures}
              className="min-h-11 cursor-pointer rounded-full px-4 py-2 text-sm font-medium text-ink-faint transition-colors hover:text-clay"
            >
              Tout désactiver
            </button>
          )}
        </div>

        {/* Measure cards */}
        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3 print:hidden">
          {CARD_ORDER.map((type, i) => {
            const active = activeMeasures.has(type);
            const cost = output.measure_costs[type];
            const info = MEASURE_LABELS[type];
            return (
              <motion.div
                key={type}
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05, duration: 0.4 }}
                className={`relative rounded-3xl border p-5 transition-all duration-300 ${
                  active
                    ? "border-pine bg-pine-mist shadow-lift"
                    : "border-line bg-surface shadow-card hover:-translate-y-0.5 hover:shadow-lift"
                }`}
              >
                <button
                  type="button"
                  aria-pressed={active}
                  onClick={() => toggleMeasure(type)}
                  className="flex w-full cursor-pointer items-start gap-3 text-left"
                >
                  <span
                    className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl transition-colors ${
                      active ? "bg-pine text-on-pine" : "bg-pine-soft text-pine"
                    }`}
                  >
                    {MEASURE_ICONS[type]}
                  </span>
                  <span className="flex-1">
                    <span className="flex items-center justify-between gap-2">
                      <span className="text-sm font-semibold">{info.title}</span>
                      <span
                        aria-hidden
                        className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full border-2 transition-all ${
                          active ? "border-pine bg-pine text-on-pine" : "border-line-strong bg-surface"
                        }`}
                      >
                        {active && <Check size={13} />}
                      </span>
                    </span>
                    <span className="mt-1 block text-xs leading-relaxed text-ink-soft">
                      {info.description}
                    </span>
                    <span className="mt-2 block text-xs font-semibold text-amber-deep tabular">
                      {formatEuroRange(cost.low_eur, cost.high_eur)}
                    </span>
                    {(badges.mostProfitable === type ||
                      badges.biggestCo2 === type ||
                      improvesSummer(type)) && (
                      <span className="mt-2 flex flex-wrap gap-1.5">
                        {badges.mostProfitable === type && (
                          <span className="inline-flex items-center gap-1 rounded-full bg-pine-soft px-2 py-0.5 text-[11px] font-semibold text-pine-deep">
                            <PiggyBank size={12} aria-hidden />
                            Le plus rentable
                          </span>
                        )}
                        {badges.biggestCo2 === type && (
                          <span className="inline-flex items-center gap-1 rounded-full bg-pine-soft px-2 py-0.5 text-[11px] font-semibold text-pine-deep">
                            <Leaf size={12} aria-hidden />
                            Plus gros gain CO₂
                          </span>
                        )}
                        {improvesSummer(type) && (
                          <span className="inline-flex items-center gap-1 rounded-full bg-amber-soft px-2 py-0.5 text-[11px] font-semibold text-amber-deep">
                            <Sun size={12} aria-hidden />
                            Confort d'été
                          </span>
                        )}
                      </span>
                    )}
                  </span>
                </button>

                {active && (
                  <div className="mt-3 border-t border-pine/20 pt-1">
                    {type === "window_replacement" && (
                      <label className="block text-xs font-medium text-ink-soft">
                        Vitrage cible
                        <select
                          className={selectClass}
                          value={params.windowGlazing}
                          onChange={(e) =>
                            updateParams({
                              windowGlazing: e.target.value as typeof params.windowGlazing,
                            })
                          }
                        >
                          <option value="double_glazing_low_e">
                            {GLAZING_LABELS.double_glazing_low_e}
                          </option>
                          <option value="triple_glazing">{GLAZING_LABELS.triple_glazing}</option>
                        </select>
                      </label>
                    )}
                    {type === "heating_replacement" && (
                      <label className="block text-xs font-medium text-ink-soft">
                        Nouveau générateur
                        <select
                          className={selectClass}
                          value={params.heatingTarget}
                          onChange={(e) =>
                            updateParams({
                              heatingTarget: e.target.value as typeof params.heatingTarget,
                            })
                          }
                        >
                          <option value="heat_pump_air_water">Pompe à chaleur air/eau</option>
                          <option value="condensing_boiler">Chaudière gaz à condensation</option>
                          <option value="wood_pellet_stove">Poêle à granulés</option>
                        </select>
                        {params.heatingTarget === "wood_pellet_stove" &&
                          form.dhw === "coupled_to_heating_system" && (
                            <span className="mt-1.5 block font-normal text-ink-faint">
                              Un poêle ne produit pas d'eau chaude : elle passe sur un ballon
                              électrique, sauf si vous activez aussi le chauffe-eau
                              thermodynamique.
                            </span>
                          )}
                      </label>
                    )}
                    {type === "ventilation_upgrade" && (
                      <label className="block text-xs font-medium text-ink-soft">
                        Nouvelle VMC
                        <select
                          className={selectClass}
                          value={params.ventilationTarget}
                          onChange={(e) =>
                            updateParams({
                              ventilationTarget: e.target.value as typeof params.ventilationTarget,
                            })
                          }
                        >
                          <option value="exhaust_only_hygro_b">
                            {VENTILATION_LABELS.exhaust_only_hygro_b}
                          </option>
                          <option value="balanced_heat_recovery">
                            {VENTILATION_LABELS.balanced_heat_recovery}
                          </option>
                        </select>
                      </label>
                    )}
                    {(type === "roof_insulation" || type === "wall_insulation") && (
                      <InsulationParams
                        material={
                          type === "roof_insulation" ? params.roofMaterial : params.wallMaterial
                        }
                        thicknessCm={
                          type === "roof_insulation"
                            ? params.roofThicknessCm
                            : params.wallThicknessCm
                        }
                        onMaterial={(m) =>
                          updateParams(
                            type === "roof_insulation" ? { roofMaterial: m } : { wallMaterial: m },
                          )
                        }
                        onThickness={(t) =>
                          updateParams(
                            type === "roof_insulation"
                              ? { roofThicknessCm: t }
                              : { wallThicknessCm: t },
                          )
                        }
                      />
                    )}
                    {type === "dhw_upgrade" && (
                      <p className="text-xs text-ink-faint">
                        Remplace l'eau chaude actuelle par un chauffe-eau thermodynamique.
                      </p>
                    )}
                  </div>
                )}
              </motion.div>
            );
          })}
        </div>

        {/* "Que faut-il pour atteindre C ?" — cheapest bundle per target class */}
        {baseline.label && (
          <LabelTargets
            baselineLabel={baseline.label}
            targets={output.label_targets}
            onApply={applyBundle}
          />
        )}

        {scenarios.length === 0 ? (
          <div className="mt-10 rounded-3xl border border-dashed border-line-strong bg-surface p-10 text-center print:hidden">
            <Lightbulb size={28} className="mx-auto text-amber" aria-hidden />
            <p className="mt-3 font-medium">Activez au moins un geste pour voir son impact.</p>
            <p className="mt-1 text-sm text-ink-soft">
              Astuce : commencez par un bouquet prédéfini ci-dessus, puis affinez.
            </p>
          </div>
        ) : (
          <>
            {/* Comparison table */}
            <section aria-label="Comparaison des scénarios" className="mt-10">
              <div className="flex items-center gap-2">
                <h2 className="font-display text-2xl font-semibold">Comparaison</h2>
                <InfoTip
                  text={
                    isPerso
                      ? "Économies calculées avec vos réglages personnalisés ; les étiquettes restent conventionnelles (règle du DPE)."
                      : "Calcul en mode conventionnel DPE : 19 °C, occupation standard, tarifs réglementés."
                  }
                />
              </div>
              <div className="mt-4 overflow-x-auto rounded-3xl border border-line bg-surface shadow-card">
                <table className="w-full min-w-[760px] text-sm">
                  <thead>
                    <tr className="border-b border-line text-left text-xs text-ink-faint">
                      <th scope="col" className="px-5 py-3.5 font-semibold">Scénario</th>
                      <th scope="col" className="px-4 py-3.5 font-semibold">Étiquette</th>
                      <th scope="col" className="px-4 py-3.5 text-right font-semibold">
                        Conso après
                        <span className="block font-normal">kWhep/m²·an</span>
                      </th>
                      <th scope="col" className="px-4 py-3.5 text-right font-semibold">
                        Économies
                        <span className="block font-normal">€/an</span>
                      </th>
                      <th scope="col" className="px-4 py-3.5 text-right font-semibold">
                        CO₂ évité
                        <span className="block font-normal">par an</span>
                      </th>
                      <th scope="col" className="px-4 py-3.5 text-right font-semibold">
                        Travaux
                        <span className="block font-normal">fourchette</span>
                      </th>
                      <th scope="col" className="px-4 py-3.5 text-right font-semibold">
                        Retour
                        <span className="block font-normal">simple</span>
                      </th>
                      <th scope="col" className="px-4 py-3.5 text-right font-semibold">
                        Confort d'été
                        <span className="block font-normal">passif</span>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {[...singles, ...(bouquet ? [bouquet] : [])].map((s) => {
                      const a = assessment(s, isPerso);
                      const conv = s.conventional;
                      const isBouquet = s.id === "bouquet";
                      return (
                        <tr
                          key={s.id}
                          className={`border-b border-line last:border-0 ${
                            isBouquet ? "bg-pine-mist font-medium" : ""
                          }`}
                        >
                          <th scope="row" className="px-5 py-3.5 text-left font-medium">
                            {scenarioTitle(s.id)}
                            {isBouquet && (
                              <span className="ml-2 rounded-full bg-pine px-2 py-0.5 text-[10px] font-bold text-on-pine uppercase">
                                {s.measures.length} gestes
                              </span>
                            )}
                          </th>
                          <td className="px-4 py-3.5">
                            <span className="inline-flex items-center gap-1.5">
                              {baseline.label && (
                                <span className="opacity-45">
                                  <DpeBadge label={baseline.label} />
                                </span>
                              )}
                              <ArrowRight size={13} className="text-ink-faint" aria-hidden />
                              {conv.after.label && <DpeBadge label={conv.after.label} />}
                            </span>
                          </td>
                          <td className="px-4 py-3.5 text-right tabular">
                            {formatInt(conv.after.primary_energy_kwh_m2)}
                          </td>
                          <td className="px-4 py-3.5 text-right font-semibold text-pine tabular">
                            {formatEuros(a.annual_savings_eur)}
                          </td>
                          <td className="px-4 py-3.5 text-right tabular">
                            {formatKgCo2(a.annual_co2_savings_kg)}
                          </td>
                          <td className="px-4 py-3.5 text-right tabular">
                            {formatEuroRange(a.investment_low_eur, a.investment_high_eur)}
                          </td>
                          <td className="px-4 py-3.5 text-right tabular">
                            {a.payback_years_low === null
                              ? "> 30 ans"
                              : `${formatPayback(a.payback_years_low)} – ${formatPayback(a.payback_years_high)}`}
                          </td>
                          <td className="px-4 py-3.5 text-right text-xs">
                            <SummerDelta
                              before={summerBefore}
                              after={s.summer_comfort_after.level}
                            />
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {bouquet && singles.length >= 2 && (
                <p className="mt-4 flex items-start gap-2 rounded-2xl bg-amber-soft px-5 py-4 text-sm leading-relaxed text-ink-soft">
                  <Info size={16} className="mt-0.5 shrink-0 text-amber-deep" aria-hidden />
                  <span>
                    <strong className="text-ink">Les gestes interagissent :</strong> votre bouquet
                    économise {formatEuros(assessment(bouquet, isPerso).annual_savings_eur)}/an,
                    alors que la somme des gestes pris isolément donnerait{" "}
                    {formatEuros(sumSingleSavings)}/an. Une fois la maison isolée, le chauffage a
                    moins à fournir — chaque kWh ne peut être économisé qu'une fois. D'où l'intérêt
                    de penser enveloppe d'abord, systèmes ensuite.
                  </span>
                </p>
              )}
            </section>

            {/* Cost vs gain chart */}
            <section
              aria-label="Coût des travaux contre économies annuelles"
              className="mt-8 rounded-3xl border border-line bg-surface p-6 shadow-card sm:p-8"
            >
              <div className="flex items-center gap-2">
                <h2 className="font-display text-xl font-semibold">Coût vs gain</h2>
                <InfoTip text="Chaque point est un scénario : plus il est haut à gauche, plus il rapporte par euro investi (investissement = milieu de la fourchette)." />
              </div>
              <Suspense
                fallback={
                  <div className="flex h-80 items-center justify-center text-sm text-ink-faint">
                    Chargement du graphique…
                  </div>
                }
              >
                <CostGainChart
                  points={[...singles, ...(bouquet ? [bouquet] : [])].map((s) => {
                    const a = assessment(s, isPerso);
                    return {
                      id: s.id,
                      name: SHORT_TITLES[s.id] ?? scenarioTitle(s.id),
                      investment: (a.investment_low_eur + a.investment_high_eur) / 2,
                      savings: a.annual_savings_eur,
                      bouquet: s.id === "bouquet",
                    };
                  })}
                />
              </Suspense>
            </section>
          </>
        )}

        <p className="mt-8 text-center text-xs leading-relaxed text-ink-faint">
          Coûts en fourchettes, hors aides financières (MaPrimeRénov', CEE…)
          {output && <>, actualisés à {formatMonth(output.conventions.renovation_costs.reference_period)} (indice
          INSEE {output.conventions.renovation_costs.index})</>}. Pour connaître vos
          aides, rendez-vous sur{" "}
          <a
            href="https://france-renov.gouv.fr"
            target="_blank"
            rel="noreferrer"
            className="font-medium text-pine hover:underline"
          >
            France Rénov'
          </a>
          . Outil pédagogique — ne remplace ni un DPE officiel ni un audit énergétique.
        </p>
      </motion.div>
    </div>
  );
}

/** Insulation card parameters: material dropdown + thickness, with a live R preview. */
function InsulationParams({
  material,
  thicknessCm,
  onMaterial,
  onThickness,
}: {
  material: InsulationMaterial;
  thicknessCm: number;
  onMaterial: (material: InsulationMaterial) => void;
  onThickness: (thicknessCm: number) => void;
}) {
  return (
    <div className="space-y-2">
      <label className="block text-xs font-medium text-ink-soft">
        Isolant
        <select
          className={selectClass}
          value={material}
          onChange={(e) => onMaterial(e.target.value as InsulationMaterial)}
        >
          {INSULATION_MATERIAL_ORDER.map((m) => (
            <option key={m} value={m}>
              {INSULATION_MATERIAL_LABELS[m]}
            </option>
          ))}
        </select>
      </label>
      <label className="block text-xs font-medium text-ink-soft">
        Épaisseur (cm)
        <input
          type="number"
          inputMode="decimal"
          min={1}
          max={60}
          step={1}
          value={thicknessCm}
          onChange={(e) => {
            const v = Number(e.target.value);
            if (!Number.isNaN(v)) onThickness(Math.min(60, Math.max(1, v)));
          }}
          className="mt-2 w-full rounded-xl border border-line bg-surface px-3 py-2 text-xs font-medium text-ink outline-none tabular focus:border-pine"
        />
      </label>
      <p className="text-xs text-ink-faint tabular">
        soit R ≈{" "}
        {addedRPreview(material, thicknessCm).toLocaleString("fr-FR", {
          maximumFractionDigits: 1,
        })}{" "}
        m²·K/W
      </p>
    </div>
  );
}

function assessment(scenario: ScenarioOutput, isPerso: boolean) {
  return isPerso && scenario.personalized ? scenario.personalized : scenario.conventional;
}

/**
 * "Par où commencer" badges from the conventional single-measure previews:
 * the most profitable gesture (lowest positive simple payback) and the one
 * with the biggest annual CO₂ saving. Ties and non-positive savings excluded.
 */
function pickMeasureBadges(previews: Record<MeasureType, MeasurePreview>): {
  mostProfitable: MeasureType | null;
  biggestCo2: MeasureType | null;
} {
  const entries = Object.entries(previews) as [MeasureType, MeasurePreview][];
  let mostProfitable: MeasureType | null = null;
  let bestPayback = Infinity;
  let biggestCo2: MeasureType | null = null;
  let bestCo2 = 0;
  for (const [type, p] of entries) {
    if (p.payback_years_low != null && p.annual_savings_eur > 0 && p.payback_years_low < bestPayback) {
      bestPayback = p.payback_years_low;
      mostProfitable = type;
    }
    if (p.annual_co2_savings_kg > bestCo2) {
      bestCo2 = p.annual_co2_savings_kg;
      biggestCo2 = type;
    }
  }
  return { mostProfitable, biggestCo2 };
}
