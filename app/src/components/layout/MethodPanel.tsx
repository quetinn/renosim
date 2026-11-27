import { AnimatePresence, motion } from "motion/react";
import { ExternalLink, X } from "lucide-react";
import { useEffect, useRef } from "react";
import { useEngine } from "../../pyodide/PyodideContext";

const REPO_URL = "https://github.com/quetinn/renosim";
/** Quarto rendering of validation/report/note_validation.md, published by deploy.yml. */
const VALIDATION_NOTE_URL = `${import.meta.env.BASE_URL}validation/index.html`;

/**
 * "Comment est-ce calculé ?" — the transparency panel required by CLAUDE.md
 * §6.3, reachable from every screen through the header.
 */
export function MethodPanel({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { engine } = useEngine();
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.button
            type="button"
            aria-label="Fermer le panneau"
            className="fixed inset-0 z-50 cursor-default bg-ink/45"
            onClick={onClose}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
          />
          <motion.aside
            role="dialog"
            aria-modal="true"
            aria-label="Comment est-ce calculé ?"
            className="fixed inset-y-0 right-0 z-50 flex w-full max-w-lg flex-col overflow-y-auto bg-surface shadow-lift"
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", stiffness: 320, damping: 32 }}
          >
            <div className="sticky top-0 flex items-center justify-between border-b border-line bg-surface/95 px-6 py-4 backdrop-blur">
              <h2 className="font-display text-xl font-semibold">Comment est-ce calculé ?</h2>
              <button
                ref={closeRef}
                type="button"
                onClick={onClose}
                aria-label="Fermer"
                className="flex h-11 w-11 cursor-pointer items-center justify-center rounded-full text-ink-soft transition-colors hover:bg-cream hover:text-ink"
              >
                <X size={20} aria-hidden />
              </button>
            </div>

            <div className="space-y-6 px-6 py-6 text-sm leading-relaxed text-ink-soft">
              <section className="space-y-2">
                <h3 className="text-base font-semibold text-ink">La méthode</h3>
                <p>
                  RénoSim implémente une version <strong>simplifiée de la méthode 3CL-DPE 2021</strong>,
                  celle des DPE officiels : déperditions de l'enveloppe (murs, toit, plancher,
                  fenêtres, ponts thermiques, ventilation), besoins de chauffage mensuels par
                  degrés-heures avec apports solaires et internes, besoins d'eau chaude, rendements
                  des systèmes, conversion en énergie primaire et en CO₂, puis étiquette.
                </p>
                <p>
                  Chaque simplification par rapport à la méthode réglementaire est documentée
                  publiquement (fichier <code className="rounded bg-cream px-1">deviations.md</code> du
                  dépôt) : ponts thermiques forfaitaires, orientation moyenne des baies, géométrie
                  reconstituée à partir de la surface…
                </p>
              </section>

              <section className="space-y-2">
                <h3 className="text-base font-semibold text-ink">La validation</h3>
                <p>
                  Le moteur a été confronté à <strong>8 046 DPE officiels</strong> récents de maisons
                  individuelles (méthode en vigueur), tirés au hasard dans la base ouverte de
                  l'ADEME et jamais utilisés pour le régler : <strong>95 % des étiquettes prédites à
                  ±1 classe</strong> du diagnostic officiel, 55 % exactement ; 89 % à ±1 classe une
                  fois repondéré selon le parc réel. La fiabilité est meilleure pour le gaz, le bois
                  et les maisons construites entre 1975 et 2012 (95 à 99 %), plus faible pour le bâti
                  d'avant 1948 (84 %) et le chauffage électrique (92 %), où le moteur tend à
                  surestimer la consommation.{" "}
                  <a
                    href={VALIDATION_NOTE_URL}
                    target="_blank"
                    rel="noreferrer"
                    className="font-medium text-pine hover:underline"
                  >
                    Lire la note de validation
                  </a>{" "}
                  (méthode, figures, intervalles de confiance, limites).
                </p>
              </section>

              <section className="space-y-2">
                <h3 className="text-base font-semibold text-ink">Les deux modes</h3>
                <p>
                  Le <strong>mode conventionnel</strong> applique le scénario réglementaire (19 °C,
                  occupation standard) : c'est lui qui produit l'étiquette DPE. Le{" "}
                  <strong>mode personnalisé</strong> ajuste les kWh, les euros et le CO₂ à vos
                  habitudes — sans jamais changer l'étiquette, par définition du diagnostic.
                </p>
              </section>

              <section className="space-y-2">
                <h3 className="text-base font-semibold text-ink">Les coûts de travaux</h3>
                <p>
                  Les coûts affichés sont des <strong>fourchettes</strong> issues de sources
                  publiques (ADEME, observatoires des coûts), datées dans les tables du dépôt. Un
                  devis d'artisan reste la seule référence fiable pour votre projet.
                </p>
              </section>

              <section className="space-y-2">
                <h3 className="text-base font-semibold text-ink">Les limites</h3>
                <ul className="list-disc space-y-1 pl-5">
                  <li>
                    Maisons individuelles, et appartements traités logement par logement (modèle
                    plus simple, validé séparément) ; pas de DPE à l'immeuble.
                  </li>
                  <li>Pas de calcul d'aides financières — voir France Rénov'.</li>
                  <li>
                    Confort d'été estimé à partir de quelques questions ; climatisation calculée
                    comme si toute la surface était refroidie.
                  </li>
                  <li>Géométrie estimée à partir de la surface et du nombre de niveaux.</li>
                  <li>
                    Ponts thermiques et murs anciens traités de façon forfaitaire : c'est sur le
                    bâti d'avant 1975 que l'écart au DPE officiel est le plus grand.
                  </li>
                </ul>
              </section>

              <div className="space-y-2 rounded-2xl bg-cream p-4">
                <p className="font-medium text-ink">
                  Outil pédagogique — ne remplace ni un DPE officiel ni un audit énergétique.
                </p>
                <a
                  href="https://france-renov.gouv.fr"
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1.5 font-medium text-pine hover:underline"
                >
                  <ExternalLink size={14} aria-hidden />
                  Être accompagné par France Rénov'
                </a>
              </div>

              <p className="text-xs text-ink-faint">
                Moteur renosim {engine ? `v${engine.engineVersion}` : ""} — exécuté localement dans
                votre navigateur via Pyodide.{" "}
                <a
                  href={REPO_URL}
                  target="_blank"
                  rel="noreferrer"
                  className="text-pine hover:underline"
                >
                  Voir le code source
                </a>
              </p>
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}
