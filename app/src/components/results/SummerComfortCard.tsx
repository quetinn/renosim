/**
 * Passive summer-comfort indicator (#16 brique 1): the official annexe 9
 * three-level scale, displayed NEXT TO the DPE label and never merged with it.
 * The point is pedagogical: a dwelling can hold heat beautifully in winter
 * (label A) and be an oven in a heat wave.
 */
import { Check, Fan, Snowflake, Sun, Thermometer, X } from "lucide-react";
import { HELP_TEXTS, SUMMER_COMFORT_LEVEL_LABELS } from "../../i18n/fr";
import type { SimulationOutput, SummerComfortLevel } from "../../types/schema";
import { formatInt } from "../../utils/format";
import { InfoTip } from "../ui/InfoTip";

const LEVELS: SummerComfortLevel[] = ["insufficient", "medium", "good"];

/** Palette per level: chip background/text reuse the existing tokens. */
const LEVEL_STYLE: Record<SummerComfortLevel, { active: string; dot: string }> = {
  insufficient: { active: "bg-clay text-white", dot: "bg-clay" },
  medium: { active: "bg-amber text-(--color-on-amber)", dot: "bg-amber" },
  good: { active: "bg-pine text-(--color-on-pine)", dot: "bg-pine" },
};

interface CriterionRow {
  label: string;
  met: boolean;
  /** Actionable passive lever shown when the criterion is not met. */
  hint?: string;
}

export function SummerComfortCard({
  summer,
}: {
  summer: SimulationOutput["summer_comfort"];
}) {
  const { level, criteria } = summer;

  const rows: CriterionRow[] = [
    ...(criteria.roof_criterion_applicable
      ? [
          {
            label: "Toiture isolée",
            met: criteria.roof_insulated,
            hint: "isoler la toiture (bloque la chaleur d'été comme celle d'hiver)",
          },
        ]
      : []),
    {
      label: "Volets ou brise-soleil extérieurs",
      met: criteria.solar_protections_full,
      hint: "équiper les fenêtres sud/est/ouest de protections extérieures",
    },
    { label: "Bonne inertie (murs lourds)", met: criteria.heavy_inertia },
    {
      label: "Logement traversant",
      met: criteria.through_dwelling,
      hint: "la ventilation nocturne traversante évacue la chaleur accumulée",
    },
    { label: "Brasseurs d'air fixes", met: criteria.fixed_air_circulators },
  ];

  return (
    <section
      aria-label="Confort d'été passif estimé"
      className="mt-6 rounded-3xl border border-line bg-surface p-6 shadow-card sm:p-8"
    >
      <div className="mb-4 flex items-center justify-between">
        <h2 className="flex items-center gap-2 font-display text-xl font-semibold">
          <Sun size={20} className="text-amber" aria-hidden />
          Confort d'été (sans climatisation)
        </h2>
        <InfoTip text={HELP_TEXTS.summerComfort} />
      </div>

      <div className="flex flex-wrap items-center gap-4">
        {/* Three-level pastille, official scale */}
        <div
          role="img"
          aria-label={`Confort d'été passif : ${SUMMER_COMFORT_LEVEL_LABELS[level]}`}
          className="flex overflow-hidden rounded-full border border-line"
        >
          {LEVELS.map((l) => (
            <span
              key={l}
              className={`px-3.5 py-1.5 text-xs font-semibold transition-colors ${
                l === level ? LEVEL_STYLE[l].active : "bg-cream text-ink-faint"
              }`}
            >
              {SUMMER_COMFORT_LEVEL_LABELS[l]}
            </span>
          ))}
        </div>
        <p className="min-w-48 flex-1 text-xs leading-relaxed text-ink-soft">
          L'étiquette DPE mesure l'hiver : un logement très bien noté peut rester étouffant en
          été. Cet indicateur officiel évalue votre résistance passive à la canicule.
        </p>
      </div>

      <ul className="mt-5 grid gap-x-6 gap-y-2 sm:grid-cols-2">
        {rows.map((row) => (
          <li key={row.label} className="flex items-start gap-2 text-xs">
            {row.met ? (
              <Check size={14} className="mt-0.5 shrink-0 text-pine" aria-hidden />
            ) : (
              <X size={14} className="mt-0.5 shrink-0 text-clay" aria-hidden />
            )}
            <span className={row.met ? "font-medium" : "text-ink-soft"}>
              {row.label}
              {!row.met && row.hint && (
                <span className="block text-ink-faint">Levier : {row.hint}.</span>
              )}
            </span>
          </li>
        ))}
      </ul>

      {summer.cooling_need_kwh > 0 && (
        <div className="mt-4 flex items-start gap-2 text-xs leading-relaxed text-ink-soft">
          <Thermometer size={14} className="mt-0.5 shrink-0 text-clay" aria-hidden />
          <span>
            Besoin de froid conventionnel :{" "}
            <strong className="tabular">
              {formatInt(summer.cooling_need_kwh)} kWh/an
            </strong>{" "}
            ({summer.cooling_need_kwh_m2.toLocaleString("fr-FR", { maximumFractionDigits: 1 })}{" "}
            kWh/m²) — la chaleur à extraire pour tenir 28 °C en été
            {summer.air_conditioning ? "" : ", si vous climatisiez"}.
          </span>
          <InfoTip text={HELP_TEXTS.coolingNeed} />
        </div>
      )}

      {summer.air_conditioning && (
        <p className="mt-4 flex items-start gap-2 rounded-xl bg-cream px-4 py-3 text-xs leading-relaxed text-ink-soft">
          <Snowflake size={14} className="mt-0.5 shrink-0 text-pine" aria-hidden />
          Logement équipé d'une climatisation : elle garantit un bon confort d'été mais augmente
          les consommations énergétiques. L'indicateur ci-dessus reste évalué sans climatisation.
        </p>
      )}
      {!summer.air_conditioning && level === "insufficient" && (
        <p className="mt-4 flex items-start gap-2 rounded-xl bg-amber-soft px-4 py-3 text-xs leading-relaxed text-ink-soft">
          <Fan size={14} className="mt-0.5 shrink-0 text-amber-deep" aria-hidden />
          Avant d'envisager une climatisation, les leviers passifs ci-dessus (volets extérieurs,
          isolation de toiture, ventilation nocturne) réduisent durablement la surchauffe — sans
          consommer d'électricité.
        </p>
      )}
    </section>
  );
}
