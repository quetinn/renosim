import { AnimatePresence, motion } from "motion/react";
import { ArrowLeft, ArrowRight, Check, MapPin, Sparkles } from "lucide-react";
import { useState } from "react";
import { climateZoneFromPostalCode } from "../../data/climateZones";
import {
  ADJACENCY_LABELS,
  ALTITUDE_LABELS,
  DHW_LABELS,
  GLAZING_LABELS,
  HEATING_AGE_LABELS,
  HEATING_LABELS,
  HELP_TEXTS,
  INSULATION_STATE_LABELS,
  PERIOD_LABELS,
  VENTILATION_LABELS,
} from "../../i18n/fr";
import { useAppState } from "../../state/AppState";
import type { InsulationChoice } from "../../state/model";
import { Button } from "../ui/Button";
import { Field, NumberInput, RadioCards, Segmented, type Option } from "../form/fields";

const STEPS = ["Localisation", "Général", "Enveloppe", "Systèmes"] as const;

function typedOptions<T extends string>(labels: Record<T, string>): Option<T>[] {
  return (Object.entries(labels) as [T, string][]).map(([value, label]) => ({ value, label }));
}

function InsulationField({
  label,
  choice,
  onChange,
}: {
  label: string;
  choice: InsulationChoice;
  onChange: (choice: InsulationChoice) => void;
}) {
  return (
    <Field label={label} help={HELP_TEXTS.insulation}>
      <RadioCards
        name={label}
        columns={2}
        options={typedOptions(INSULATION_STATE_LABELS)}
        value={choice.state}
        onChange={(state) =>
          onChange(state === "known_r" ? { state, rValue: 3.7 } : { state })
        }
      />
      {choice.state === "known_r" && (
        <div className="flex items-center gap-3 pt-1">
          <NumberInput
            value={choice.rValue}
            onChange={(rValue) => onChange({ state: "known_r", rValue: Math.max(0.1, rValue) })}
            min={0.1}
            max={20}
            step={0.1}
            suffix="m²·K/W"
            ariaLabel={`Résistance thermique ${label}`}
          />
          <span className="text-xs text-ink-faint">R ajouté par l'isolant</span>
        </div>
      )}
    </Field>
  );
}

export function Wizard() {
  const { form, updateForm, setPeriod, setView } = useAppState();
  const [step, setStep] = useState(0);
  const [direction, setDirection] = useState(1);
  const [touchedPostal, setTouchedPostal] = useState(false);

  const zone = climateZoneFromPostalCode(form.postalCode);
  const canContinue = step === 0 ? zone !== null : true;

  const go = (delta: number) => {
    setDirection(delta);
    const next = step + delta;
    if (next < 0) {
      setView("landing");
    } else if (next >= STEPS.length) {
      setView("results");
    } else {
      setStep(next);
      window.scrollTo({ top: 0 });
    }
  };

  return (
    <div className="mx-auto max-w-3xl px-4 py-10 sm:px-6">
      {/* Stepper */}
      <ol className="flex items-center gap-1 sm:gap-2" aria-label="Étapes du parcours">
        {STEPS.map((label, i) => {
          const done = i < step;
          const current = i === step;
          return (
            <li key={label} className="flex flex-1 items-center gap-1 sm:gap-2">
              <span
                aria-current={current ? "step" : undefined}
                className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-bold transition-colors ${
                  done
                    ? "bg-pine text-white"
                    : current
                      ? "border-2 border-pine bg-pine-soft text-pine-deep"
                      : "border border-line bg-surface text-ink-faint"
                }`}
              >
                {done ? <Check size={14} aria-hidden /> : i + 1}
              </span>
              <span
                className={`hidden text-xs font-medium sm:block ${
                  current ? "text-ink" : "text-ink-faint"
                }`}
              >
                {label}
              </span>
              {i < STEPS.length - 1 && (
                <span
                  aria-hidden
                  className={`h-0.5 flex-1 rounded ${done ? "bg-pine" : "bg-line"}`}
                />
              )}
            </li>
          );
        })}
      </ol>

      <div className="relative mt-8 overflow-hidden">
        <AnimatePresence mode="wait" custom={direction}>
          <motion.section
            key={step}
            custom={direction}
            initial={{ opacity: 0, x: direction * 60 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: direction * -60 }}
            transition={{ duration: 0.3, ease: [0.22, 0.65, 0.3, 1] }}
            aria-label={STEPS[step]}
            className="rounded-3xl border border-line bg-surface p-6 shadow-card sm:p-8"
          >
            {step === 0 && (
              <div className="space-y-7">
                <StepTitle
                  title="Où se situe votre maison ?"
                  subtitle="La zone climatique et l'altitude déterminent la rigueur de l'hiver dans le calcul."
                />
                <Field label="Code postal" help={HELP_TEXTS.postalCode}>
                  <div className="flex flex-wrap items-center gap-3">
                    <div className="inline-flex items-center gap-2 rounded-2xl border border-line bg-surface px-4 py-2 focus-within:border-pine">
                      <MapPin size={16} className="text-ink-faint" aria-hidden />
                      <input
                        type="text"
                        inputMode="numeric"
                        autoComplete="postal-code"
                        maxLength={5}
                        placeholder="ex. 69003"
                        value={form.postalCode}
                        onChange={(e) => {
                          updateForm({ postalCode: e.target.value.replace(/\D/g, "") });
                          setTouchedPostal(true);
                        }}
                        aria-label="Code postal"
                        aria-invalid={touchedPostal && form.postalCode.length === 5 && !zone}
                        className="w-28 border-none bg-transparent text-base font-semibold tracking-widest outline-none tabular"
                      />
                    </div>
                    {zone && (
                      <motion.span
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className="inline-flex items-center gap-1.5 rounded-full bg-pine-soft px-3.5 py-1.5 text-sm font-semibold text-pine-deep"
                      >
                        <Check size={14} aria-hidden />
                        Zone climatique {zone}
                      </motion.span>
                    )}
                    {touchedPostal && form.postalCode.length === 5 && !zone && (
                      <span role="alert" className="text-sm font-medium text-clay">
                        Code postal non reconnu (métropole uniquement en V1).
                      </span>
                    )}
                  </div>
                </Field>
                <Field label="Altitude" help={HELP_TEXTS.altitude}>
                  <Segmented
                    name="Altitude"
                    options={typedOptions(ALTITUDE_LABELS)}
                    value={form.altitude}
                    onChange={(altitude) => updateForm({ altitude })}
                  />
                </Field>
              </div>
            )}

            {step === 1 && (
              <div className="space-y-7">
                <StepTitle
                  title="Parlez-nous de la maison"
                  subtitle="L'année de construction pré-remplit l'isolation et les équipements typiques de l'époque — ajustables à l'étape suivante."
                />
                <Field label="Surface habitable" help={HELP_TEXTS.livingArea}>
                  <NumberInput
                    value={form.livingArea}
                    onChange={(v) => updateForm({ livingArea: Math.min(600, Math.max(15, v)) })}
                    min={15}
                    max={600}
                    suffix="m²"
                    ariaLabel="Surface habitable en mètres carrés"
                  />
                </Field>
                <Field label="Période de construction" help={HELP_TEXTS.period}>
                  <RadioCards
                    name="Période de construction"
                    columns={3}
                    options={typedOptions(PERIOD_LABELS)}
                    value={form.period}
                    onChange={setPeriod}
                  />
                </Field>
                <div className="grid gap-7 sm:grid-cols-2">
                  <Field label="Niveaux chauffés" help={HELP_TEXTS.levels}>
                    <Segmented
                      name="Niveaux chauffés"
                      options={[
                        { value: "1", label: "1" },
                        { value: "2", label: "2" },
                        { value: "3", label: "3" },
                      ]}
                      value={String(form.levels) as "1" | "2" | "3"}
                      onChange={(v) => updateForm({ levels: Number(v) })}
                    />
                  </Field>
                  <Field label="Mitoyenneté" help={HELP_TEXTS.adjacency}>
                    <Segmented
                      name="Mitoyenneté"
                      options={typedOptions(ADJACENCY_LABELS)}
                      value={form.adjacency}
                      onChange={(adjacency) => updateForm({ adjacency })}
                    />
                  </Field>
                </div>
              </div>
            )}

            {step === 2 && (
              <div className="space-y-7">
                <StepTitle
                  title="L'enveloppe : par où la chaleur peut fuir"
                  subtitle="En cas de doute, gardez « Isolation d'origine / je ne sais pas » : le calcul applique les valeurs réglementaires de l'époque."
                />
                <InsulationField
                  label="Combles / toiture"
                  choice={form.roofInsulation}
                  onChange={(roofInsulation) => updateForm({ roofInsulation })}
                />
                <InsulationField
                  label="Murs extérieurs"
                  choice={form.wallInsulation}
                  onChange={(wallInsulation) => updateForm({ wallInsulation })}
                />
                <InsulationField
                  label="Plancher bas"
                  choice={form.floorInsulation}
                  onChange={(floorInsulation) => updateForm({ floorInsulation })}
                />
                <Field label="Vitrage" help={HELP_TEXTS.glazing}>
                  <RadioCards
                    name="Vitrage"
                    columns={2}
                    options={typedOptions(GLAZING_LABELS)}
                    value={form.glazing}
                    onChange={(glazing) => updateForm({ glazing })}
                  />
                </Field>
              </div>
            )}

            {step === 3 && (
              <div className="space-y-7">
                <StepTitle
                  title="Chauffage, eau chaude et ventilation"
                  subtitle="Le rendement dépend du type de générateur et de son âge."
                />
                <Field label="Chauffage principal">
                  <RadioCards
                    name="Chauffage principal"
                    columns={3}
                    options={typedOptions(HEATING_LABELS)}
                    value={form.heating}
                    onChange={(heating) => updateForm({ heating })}
                  />
                </Field>
                <Field label="Âge du chauffage" help={HELP_TEXTS.heatingAge}>
                  <Segmented
                    name="Âge du chauffage"
                    options={typedOptions(HEATING_AGE_LABELS)}
                    value={form.heatingAge}
                    onChange={(heatingAge) => updateForm({ heatingAge })}
                  />
                </Field>
                <Field label="Eau chaude sanitaire" help={HELP_TEXTS.dhw}>
                  <RadioCards
                    name="Eau chaude sanitaire"
                    columns={2}
                    options={typedOptions(DHW_LABELS)}
                    value={form.dhw}
                    onChange={(dhw) => updateForm({ dhw })}
                  />
                </Field>
                <Field label="Ventilation" help={HELP_TEXTS.ventilation}>
                  <RadioCards
                    name="Ventilation"
                    columns={2}
                    options={typedOptions(VENTILATION_LABELS)}
                    value={form.ventilation}
                    onChange={(ventilation) => updateForm({ ventilation })}
                  />
                </Field>
              </div>
            )}
          </motion.section>
        </AnimatePresence>
      </div>

      {/* Navigation */}
      <div className="mt-6 flex items-center justify-between gap-3">
        <Button variant="ghost" onClick={() => go(-1)}>
          <ArrowLeft size={16} aria-hidden />
          {step === 0 ? "Accueil" : "Retour"}
        </Button>
        <Button size="lg" disabled={!canContinue} onClick={() => go(1)}>
          {step === STEPS.length - 1 ? (
            <>
              Voir mes résultats
              <Sparkles size={17} aria-hidden />
            </>
          ) : (
            <>
              Continuer
              <ArrowRight size={17} aria-hidden />
            </>
          )}
        </Button>
      </div>
      {step === 0 && !zone && touchedPostal && form.postalCode.length > 0 && (
        <p className="mt-2 text-right text-xs text-ink-faint">
          Saisissez un code postal métropolitain valide pour continuer.
        </p>
      )}
    </div>
  );
}

function StepTitle({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <header className="space-y-1.5">
      <h2 className="font-display text-2xl font-semibold">{title}</h2>
      <p className="text-sm leading-relaxed text-ink-soft">{subtitle}</p>
    </header>
  );
}
