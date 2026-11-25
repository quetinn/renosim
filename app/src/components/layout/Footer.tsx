import { Code, ExternalLink, Lock } from "lucide-react";

const REPO_URL = "https://github.com/quetinn/renosim";

export function Footer() {
  return (
    <footer className="mt-auto border-t border-line bg-cream/60 print:hidden">
      <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
        <div className="flex flex-col gap-6 md:flex-row md:items-start md:justify-between">
          <div className="max-w-md space-y-2">
            <p className="font-display text-lg font-semibold">RénoSim</p>
            <p className="text-sm leading-relaxed text-ink-soft">
              Outil pédagogique open source — il ne remplace ni un DPE officiel réalisé par un
              diagnostiqueur certifié, ni un audit énergétique.
            </p>
            <p className="inline-flex items-center gap-1.5 text-sm font-medium text-pine">
              <Lock size={14} aria-hidden />
              Vos données restent dans votre navigateur : aucun serveur, aucun envoi.
            </p>
          </div>
          <nav aria-label="Liens utiles" className="grid gap-2 text-sm">
            <a
              href="https://france-renov.gouv.fr"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 text-ink-soft transition-colors hover:text-pine"
            >
              <ExternalLink size={14} aria-hidden />
              France Rénov' — conseils et aides officielles
            </a>
            <a
              href={REPO_URL}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 text-ink-soft transition-colors hover:text-pine"
            >
              <Code size={14} aria-hidden />
              Code source, méthode et note de validation
            </a>
          </nav>
        </div>
        <p className="mt-8 text-xs text-ink-faint">
          Moteur inspiré de la méthode 3CL-DPE 2021 (simplifiée, écarts documentés) — confronté à
          la base des DPE de l'ADEME. Licence MIT.
        </p>
      </div>
    </footer>
  );
}
