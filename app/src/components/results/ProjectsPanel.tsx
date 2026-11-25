import { FolderOpen, Save, Trash2 } from "lucide-react";
import { useState } from "react";
import { useAppState } from "../../state/AppState";
import { formatInt } from "../../utils/format";
import { Button } from "../ui/Button";
import { InfoTip } from "../ui/InfoTip";
import { DpeBadge } from "./DpeScale";

/**
 * "Mes logements" (#12): save the current description under a name and compare
 * several saved homes side by side (conventional summaries captured at save
 * time). Everything stays in localStorage — nothing leaves the browser.
 */
export function ProjectsPanel() {
  const { form, output, projects, saveProject, loadProject, deleteProject } = useAppState();
  const zone = form.postalCode ? ` ${form.postalCode}` : "";
  const [name, setName] = useState("");
  const placeholder = `Maison${zone} · ${formatInt(form.livingArea)} m²`;

  const current = output?.baseline.conventional;

  return (
    <section
      aria-label="Mes logements enregistrés"
      className="mt-6 rounded-3xl border border-line bg-surface p-6 shadow-card print:hidden sm:p-8"
    >
      <div className="flex items-center gap-2">
        <h2 className="font-display text-xl font-semibold">Mes logements</h2>
        <InfoTip text="Enregistrez plusieurs logements ou variantes (annonces immobilières, avant/après travaux) et comparez-les. Tout reste dans votre navigateur." />
      </div>

      <form
        className="mt-4 flex flex-wrap items-center gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          saveProject(name.trim() || placeholder);
          setName("");
        }}
      >
        <input
          type="text"
          value={name}
          maxLength={60}
          placeholder={placeholder}
          aria-label="Nom du logement à enregistrer"
          onChange={(e) => setName(e.target.value)}
          className="min-h-11 w-64 rounded-2xl border border-line bg-surface px-4 py-2 text-sm font-medium text-ink outline-none focus:border-pine"
        />
        <Button type="submit" variant="outline">
          <Save size={15} aria-hidden />
          Enregistrer ce logement
        </Button>
      </form>

      {projects.length > 0 && (
        <div className="mt-5 overflow-x-auto">
          <table className="w-full min-w-[560px] text-sm">
            <thead>
              <tr className="border-b border-line text-left text-xs text-ink-faint">
                <th scope="col" className="py-2.5 pr-4 font-semibold">Logement</th>
                <th scope="col" className="px-3 py-2.5 font-semibold">Étiquette</th>
                <th scope="col" className="px-3 py-2.5 text-right font-semibold">kWhep/m²·an</th>
                <th scope="col" className="px-3 py-2.5 text-right font-semibold">€/an</th>
                <th scope="col" className="px-3 py-2.5 text-right font-semibold">kgCO₂/m²·an</th>
                <th scope="col" className="px-3 py-2.5"><span className="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody>
              {current && (
                <tr className="border-b border-line bg-pine-mist">
                  <th scope="row" className="py-2.5 pr-4 text-left font-medium">
                    Simulation actuelle
                  </th>
                  <td className="px-3 py-2.5">{current.label && <DpeBadge label={current.label} />}</td>
                  <td className="px-3 py-2.5 text-right tabular">
                    {formatInt(current.primary_energy_kwh_m2)}
                  </td>
                  <td className="px-3 py-2.5 text-right tabular">
                    {formatInt(current.annual_cost_eur)}
                  </td>
                  <td className="px-3 py-2.5 text-right tabular">{formatInt(current.co2_kg_m2)}</td>
                  <td />
                </tr>
              )}
              {projects.map((p) => (
                <tr key={p.id} className="border-b border-line last:border-0">
                  <th scope="row" className="py-2.5 pr-4 text-left font-medium">
                    {p.name}
                    <span className="ml-2 text-xs font-normal text-ink-faint">
                      {new Date(p.savedAt).toLocaleDateString("fr-FR")}
                    </span>
                  </th>
                  <td className="px-3 py-2.5">
                    {p.summary?.label && <DpeBadge label={p.summary.label} />}
                  </td>
                  <td className="px-3 py-2.5 text-right tabular">
                    {p.summary ? formatInt(p.summary.primary_energy_kwh_m2) : "—"}
                  </td>
                  <td className="px-3 py-2.5 text-right tabular">
                    {p.summary ? formatInt(p.summary.annual_cost_eur) : "—"}
                  </td>
                  <td className="px-3 py-2.5 text-right tabular">
                    {p.summary ? formatInt(p.summary.co2_kg_m2) : "—"}
                  </td>
                  <td className="px-3 py-2.5">
                    <span className="flex items-center justify-end gap-1">
                      <button
                        type="button"
                        onClick={() => loadProject(p.id)}
                        title={`Charger « ${p.name} »`}
                        className="inline-flex min-h-9 cursor-pointer items-center gap-1 rounded-full px-3 text-xs font-semibold text-pine transition-colors hover:bg-pine-soft"
                      >
                        <FolderOpen size={14} aria-hidden />
                        Charger
                      </button>
                      <button
                        type="button"
                        onClick={() => deleteProject(p.id)}
                        title={`Supprimer « ${p.name} »`}
                        aria-label={`Supprimer ${p.name}`}
                        className="inline-flex min-h-9 cursor-pointer items-center rounded-full px-2.5 text-ink-faint transition-colors hover:text-clay"
                      >
                        <Trash2 size={14} aria-hidden />
                      </button>
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-2 text-xs text-ink-faint">
            Comparaison en mode conventionnel (valeurs enregistrées au moment de la sauvegarde).
          </p>
        </div>
      )}
    </section>
  );
}
