import { AnimatePresence, motion } from "motion/react";
import { ArrowLeft, ArrowRight, Check, MapPin, Sparkles } from "lucide-react";
import { useState } from "react";
import { climateZoneFromPostalCode } from "../../data/climateZones";
import { INSULATION_MATERIAL_ORDER, addedRPreview } from "../../data/insulationMaterials";
import {
  ADJACENCY_LABELS,
  ALTITUDE_LABELS,
  APARTMENT_POSITION_LABELS,
  COOLING_PERIOD_LABELS,
  DHW_LABELS,
  DWELLING_LABELS,
  FLOOR_TYPE_LABELS,
  GLAZING_LABELS,
  GLAZING_ORIENTATION_LABELS,
  HEATING_AGE_LABELS,
  HEATING_BACKUP_LABELS,
  HEATING_LABELS,
  HELP_TEXTS,
  TRI_STATE_LABELS,
  INSULATION_MATERIAL_LABELS,
  INSULATION_STATE_LABELS,
  PERIOD_LABELS,
  SOLAR_PROTECTION_LABELS,
  SOLAR_SHADING_LABELS,
  VENTILATION_LABELS,
} from "../../i18n/fr";
import { useAppState } from "../../state/AppState";
import type { GeometryState, InsulationChoice } from "../../state/model";
import { WOOD_MAIN_HEATING } from "../../state/model";
import type { InsulationMaterial } from "../../types/schema";
import { Button } from "../ui/Button";
import { InfoTip } from "../ui/InfoTip";
import { Field, NumberInput, RadioCards, Segmented, type Option } from "../form/fields";

const STEPS = ["Localisation", "Général", "Enveloppe", "Systèmes"] as const;

function typedOptions<T extends string>(labels: Record<T, string>): Option<T>[] {
  return (Object.entries(labels) as [T, string][]).map(([value, label]) => ({ value, label }));
}

/** Number input accepting an empty value (null = "let the engine estimate"). */
function OptionalNumberInput({
  label,
  suffix,
  placeholder,
  value,
  onChange,
}: {
  label: string;
  suffix: string;
  placeholder: string;
  value: number | null;
  onChange: (value: number | null) => void;
}) {
  return (
    <label className="block text-xs font-medium text-ink-soft">
      {label}
      <span className="mt-1.5 flex items-center gap-2 rounded-2xl border border-line bg-surface px-3 py-2 focus-within:border-pine">
        <input
          type="number"
          inputMode="decimal"
          min={0}
          value={value ?? ""}
          placeholder={placeholder}
          aria-label={label}
          onChange={(e) => {
            const raw = e.target.value;
            if (raw === "") {
              onChange(null);
              return;
            }
            const v = Number(raw);
            if (!Number.isNaN(v)) onChange(v);
          }}
          className="w-full border-none bg-transparent text-sm font-semibold text-ink outline-none tabular"
        />
        <span className="shrink-0 text-xs text-ink-faint">{suffix}</span>
      </span>
    </label>
  );
}

/** Collapsible "I know my surface areas" panel (optional M-1 overrides). */
function GeometryPanel({
  geometry,
  onChange,
}: {
  geometry: GeometryState;
  onChange: (geometry: GeometryState) => void;
}) {
  const patch = (p: Partial<GeometryState>) => onChange({ ...geometry, ...p });
  return (
    <details className="rounded-2xl border border-line bg-surface px-4 py-3">
      <summary className="cursor-pointer text-sm font-semibold text-ink">
        Je connais mes surfaces (optionnel)
      </summary>
      <p className="mt-2 text-xs leading-relaxed text-ink-soft">{HELP_TEXTS.geometry}</p>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <OptionalNumberInput
          label="Hauteur sous plafond"
          suffix="m"
          placeholder="2,5"
          value={geometry.ceilingHeight}
          onChange={(ceilingHeight) => patch({ ceilingHeight })}
        />
        <OptionalNumberInput
          label="Murs extérieurs (hors fenêtres)"
          suffix="m²"
          placeholder="auto"
          value={geometry.wallArea}
          onChange={(wallArea) => patch({ wallArea })}
        />
        <OptionalNumberInput
          label="Fenêtres et portes-fenêtres"
          suffix="m²"
          placeholder="auto"
          value={geometry.windowArea}
          onChange={(windowArea) => patch({ windowArea })}
        />
        <OptionalNumberInput
          label="Toiture / plafond"
          suffix="m²"
          placeholder="auto"
          value={geometry.roofArea}
          onChange={(roofArea) => patch({ roofArea })}
        />
        <OptionalNumberInput
          label="Plancher bas"
          suffix="m²"
          placeholder="auto"
          value={geometry.floorArea}
          onChange={(floorArea) => patch({ floorArea })}
        />
      </div>
    </details>
  );
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
          onChange(
            state === "known_r"
              ? { state, material: "glass_wool", thicknessCm: 20 }
              : { state },
          )
        }
      />
      {choice.state === "known_r" && (
        <div className="flex flex-wrap items-center gap-3 pt-1">
          <select
            value={choice.material}
            onChange={(e) =>
              onChange({ ...choice, material: e.target.value as InsulationMaterial })
            }
            aria-label={`Isolant ${label}`}
            className="min-h-11 cursor-pointer rounded-2xl border border-line bg-surface px-4 py-2 text-sm font-medium text-ink outline-none focus:border-pine"
          >
            {INSULATION_MATERIAL_ORDER.map((m) => (
              <option key={m} value={m}>
                {INSULATION_MATERIAL_LABELS[m]}
              </option>
            ))}
          </select>
          <NumberInput
            value={choice.thicknessCm}
            onChange={(thicknessCm) =>
              onChange({ ...choice, thicknessCm: Math.min(60, Math.max(1, thicknessCm)) })
            }
            min={1}
            max={60}
            step={1}
            suffix="cm"
            ariaLabel={`Épaisseur d'isolant ${label}`}
          />
          <span className="text-xs text-ink-faint tabular">
            soit R ≈{" "}
            {addedRPreview(choice.material, choice.thicknessCm).toLocaleString("fr-FR", {
              maximumFractionDigits: 1,
            })}{" "}
            m²·K/W
          </span>
        </div>
      )}
    </Field>
  );
}

export function Wizard() {
  const { form, updateForm, setPeriod, setView, resetAll } = useAppState();
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
                    ? "bg-pine text-on-pine"
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
                  title="Parlez-nous du logement"
                  subtitle="L'année de construction pré-remplit l'isolation et les équipements typiques de l'époque — ajustables à l'étape suivante."
                />
                <Field label="Type de logement" help={HELP_TEXTS.dwellingType}>
                  <Segmented
                    name="Type de logement"
                    options={typedOptions(DWELLING_LABELS)}
                    value={form.dwellingType}
                    onChange={(dwellingType) => updateForm({ dwellingType })}
                  />
                </Field>
                {form.dwellingType === "apartment" && (
                  <>
                    <Field label="Position dans l'immeuble" help={HELP_TEXTS.apartmentPosition}>
                      <RadioCards
                        name="Position dans l'immeuble"
                        columns={2}
                        options={typedOptions(APARTMENT_POSITION_LABELS)}
                        value={form.apartmentPosition}
                        onChange={(apartmentPosition) => updateForm({ apartmentPosition })}
                      />
                    </Field>
                    <Field label="Logement traversant" help={HELP_TEXTS.apartmentTraversant}>
                      <Segmented
                        name="Logement traversant"
                        options={[
                          { value: "yes", label: "Traversant (2 façades)" },
                          { value: "no", label: "Mono-orienté (1 façade)" },
                        ]}
                        value={form.apartmentTraversant ? "yes" : "no"}
                        onChange={(v) => updateForm({ apartmentTraversant: v === "yes" })}
                      />
                    </Field>
                  </>
                )}
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
                {form.dwellingType === "house" && (
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
                )}
                <GeometryPanel
                  geometry={form.geometry}
                  onChange={(geometry) => updateForm({ geometry })}
                />
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
                <Field label="Sous le plancher bas" help={HELP_TEXTS.floorType}>
                  <RadioCards
                    name="Sous le plancher bas"
                    columns={2}
                    options={typedOptions(FLOOR_TYPE_LABELS)}
                    value={form.floorType}
                    onChange={(floorType) => updateForm({ floorType })}
                  />
                </Field>
                <div className="space-y-4">
                  <p className="flex items-center gap-1.5 text-sm font-semibold text-ink">
                    Inertie : quelles parois sont lourdes ?
                    <InfoTip text={HELP_TEXTS.inertia} />
                  </p>
                  {(
                    [
                      ["floor", "Plancher bas lourd ?", HELP_TEXTS.inertiaFloor],
                      ["ceiling", "Plafond lourd ?", HELP_TEXTS.inertiaCeiling],
                      ["walls", "Murs lourds ?", HELP_TEXTS.inertiaWalls],
                    ] as const
                  ).map(([key, label, help]) => (
                    <Field key={key} label={label} help={help}>
                      <Segmented
                        name={label}
                        options={typedOptions(TRI_STATE_LABELS)}
                        value={form.inertiaElements[key]}
                        onChange={(value) =>
                          updateForm({ inertiaElements: { ...form.inertiaElements, [key]: value } })
                        }
                      />
                    </Field>
                  ))}
                </div>
                <Field label="Vitrage" help={HELP_TEXTS.glazing}>
                  <RadioCards
                    name="Vitrage"
                    columns={2}
                    options={typedOptions(GLAZING_LABELS)}
                    value={form.glazing}
                    onChange={(glazing) => updateForm({ glazing })}
                  />
                </Field>
                <Field
                  label="Orientation principale des fenêtres"
                  help={HELP_TEXTS.glazingOrientation}
                >
                  <RadioCards
                    name="Orientation principale des fenêtres"
                    columns={2}
                    options={typedOptions(GLAZING_ORIENTATION_LABELS)}
                    value={form.glazingOrientation}
                    onChange={(glazingOrientation) => updateForm({ glazingOrientation })}
                  />
                </Field>
                <Field label="Environnement autour de la maison" help={HELP_TEXTS.solarShading}>
                  <Segmented
                    name="Environnement autour de la maison"
                    options={typedOptions(SOLAR_SHADING_LABELS)}
                    value={form.solarShading}
                    onChange={(solarShading) => updateForm({ solarShading })}
                  />
                </Field>
                <Field
                  label="Volets ou brise-soleil extérieurs"
                  help={HELP_TEXTS.solarProtections}
                >
                  <Segmented
                    name="Volets ou brise-soleil extérieurs"
                    options={typedOptions(SOLAR_PROTECTION_LABELS)}
                    value={form.solarProtections}
                    onChange={(solarProtections) => updateForm({ solarProtections })}
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
                {!WOOD_MAIN_HEATING.includes(form.heating) && (
                  <Field label="Poêle ou insert en appoint ?" help={HELP_TEXTS.heatingBackup}>
                    <Segmented
                      name="Poêle ou insert en appoint"
                      options={typedOptions(HEATING_BACKUP_LABELS)}
                      value={form.heatingBackup}
                      onChange={(heatingBackup) => updateForm({ heatingBackup })}
                    />
                  </Field>
                )}
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
                <div className="grid gap-7 sm:grid-cols-2">
                  <Field label="Brasseurs d'air fixes" help={HELP_TEXTS.fixedAirCirculators}>
                    <Segmented
                      name="Brasseurs d'air fixes"
                      options={[
                        { value: "no", label: "Non" },
                        { value: "yes", label: "Oui" },
                      ]}
                      value={form.fixedAirCirculators ? "yes" : "no"}
                      onChange={(v) => updateForm({ fixedAirCirculators: v === "yes" })}
                    />
                  </Field>
                  <Field label="Climatisation" help={HELP_TEXTS.airConditioning}>
                    <Segmented
                      name="Climatisation"
                      options={[
                        { value: "no", label: "Non" },
                        { value: "yes", label: "Oui" },
                      ]}
                      value={form.airConditioning ? "yes" : "no"}
                      onChange={(v) => updateForm({ airConditioning: v === "yes" })}
                    />
                  </Field>
                </div>
                {form.airConditioning && (
                  <Field
                    label="Installation de la climatisation"
                    help={HELP_TEXTS.airConditioningPeriod}
                  >
                    <Segmented
                      name="Installation de la climatisation"
                      options={typedOptions(COOLING_PERIOD_LABELS)}
                      value={
                        form.airConditioningPeriod === "unknown"
                          ? "from_2015"
                          : form.airConditioningPeriod
                      }
                      onChange={(airConditioningPeriod) =>
                        updateForm({ airConditioningPeriod })
                      }
                    />
                  </Field>
                )}
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
      <p className="mt-6 text-center">
        <button
          type="button"
          onClick={() => {
            resetAll();
            setStep(0);
          }}
          className="cursor-pointer text-xs text-ink-faint underline-offset-2 transition-colors hover:text-clay hover:underline"
        >
          Effacer mes réponses et repartir de zéro
        </button>
      </p>
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
