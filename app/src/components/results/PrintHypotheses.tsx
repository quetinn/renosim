import { climateZoneFromPostalCode } from "../../data/climateZones";
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
  INERTIA_LABELS,
  TRI_STATE_LABELS,
  INSULATION_MATERIAL_LABELS,
  INSULATION_STATE_LABELS,
  PERIOD_LABELS,
  SOLAR_PROTECTION_LABELS,
  SOLAR_SHADING_LABELS,
  VENTILATION_LABELS,
} from "../../i18n/fr";
import type { FormState } from "../../state/model";
import type { InsulationChoice } from "../../state/model";
import { WOOD_MAIN_HEATING } from "../../state/model";
import { formatInt } from "../../utils/format";

function insulationText(choice: InsulationChoice): string {
  if (choice.state === "known_r") {
    return `${INSULATION_MATERIAL_LABELS[choice.material]}, ${choice.thicknessCm} cm`;
  }
  return INSULATION_STATE_LABELS[choice.state];
}

/**
 * Print-only recap of every simulation input (backlog #11): the printed /
 * PDF-exported report then carries its own hypotheses, per the brief's
 * transparency requirement. Hidden on screen.
 */
export function PrintHypotheses({ form }: { form: FormState }) {
  const zone = climateZoneFromPostalCode(form.postalCode);
  const isApartment = form.dwellingType === "apartment";
  const rows: [string, string][] = [
    ["Localisation", `${form.postalCode} (zone ${zone ?? "?"}) — ${ALTITUDE_LABELS[form.altitude]}`],
    ["Type de logement", DWELLING_LABELS[form.dwellingType]],
    [
      "Surface habitable",
      isApartment
        ? `${formatInt(form.livingArea)} m²`
        : `${formatInt(form.livingArea)} m² — ${form.levels} niveau(x)`,
    ],
    ["Période de construction", PERIOD_LABELS[form.period]],
    ...(isApartment
      ? ([
          ["Position dans l'immeuble", APARTMENT_POSITION_LABELS[form.apartmentPosition]],
          ["Exposition", form.apartmentTraversant ? "Traversant" : "Mono-orienté"],
        ] as [string, string][])
      : ([["Mitoyenneté", ADJACENCY_LABELS[form.adjacency]]] as [string, string][])),
    ["Combles / toiture", insulationText(form.roofInsulation)],
    ["Murs extérieurs", insulationText(form.wallInsulation)],
    ["Plancher bas", insulationText(form.floorInsulation)],
    ["Sous le plancher bas", FLOOR_TYPE_LABELS[form.floorType]],
    ["Vitrage", GLAZING_LABELS[form.glazing]],
    ["Orientation des fenêtres", GLAZING_ORIENTATION_LABELS[form.glazingOrientation]],
    ["Masques solaires", SOLAR_SHADING_LABELS[form.solarShading]],
    [
      "Inertie",
      Object.values(form.inertiaElements).some((v) => v !== "unknown")
        ? `parois lourdes : plancher bas ${TRI_STATE_LABELS[form.inertiaElements.floor].toLowerCase()}, plafond ${TRI_STATE_LABELS[form.inertiaElements.ceiling].toLowerCase()}, murs ${TRI_STATE_LABELS[form.inertiaElements.walls].toLowerCase()}`
        : INERTIA_LABELS[form.inertia],
    ],
    [
      "Chauffage",
      `${HEATING_LABELS[form.heating]} — ${HEATING_AGE_LABELS[form.heatingAge].toLowerCase()}`,
    ],
    ...(form.heatingBackup !== "none" && !WOOD_MAIN_HEATING.includes(form.heating)
      ? ([["Appoint (¼ de la chaleur)", HEATING_BACKUP_LABELS[form.heatingBackup]]] as [
          string,
          string,
        ][])
      : []),
    ["Eau chaude sanitaire", DHW_LABELS[form.dhw]],
    ["Ventilation", VENTILATION_LABELS[form.ventilation]],
    ["Protections solaires extérieures", SOLAR_PROTECTION_LABELS[form.solarProtections]],
    ["Brasseurs d'air fixes", form.fixedAirCirculators ? "Oui" : "Non"],
    [
      "Climatisation",
      form.airConditioning
        ? `Oui — ${COOLING_PERIOD_LABELS[
            form.airConditioningPeriod === "unknown" ? "from_2015" : form.airConditioningPeriod
          ].toLowerCase()}`
        : "Non",
    ],
  ];
  return (
    <section aria-hidden className="mt-6 hidden rounded-3xl border border-line p-6 print:block">
      <h2 className="font-display text-lg font-semibold">Hypothèses de la simulation</h2>
      <dl className="mt-3 grid grid-cols-2 gap-x-8 gap-y-1.5 text-xs">
        {rows.map(([label, value]) => (
          <div key={label} className="flex justify-between gap-3 border-b border-line/60 py-1">
            <dt className="text-ink-faint">{label}</dt>
            <dd className="text-right font-medium">{value}</dd>
          </div>
        ))}
      </dl>
      <p className="mt-3 text-[10px] leading-relaxed text-ink-faint">
        Les champs non renseignés utilisent les valeurs conventionnelles de la méthode 3CL-DPE
        2021 (simplifiée, écarts documentés dans le dépôt du projet). Moteur RénoSim — calcul
        exécuté localement dans le navigateur.
      </p>
    </section>
  );
}
