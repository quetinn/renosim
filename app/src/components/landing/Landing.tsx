import { motion, useReducedMotion, useScroll, useTransform } from "motion/react";
import {
  ArrowRight,
  BookOpen,
  ClipboardList,
  Code,
  ExternalLink,
  Home,
  Lock,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { useRef } from "react";
import { useAppState } from "../../state/AppState";
import { Button } from "../ui/Button";
import { CountUp } from "../ui/CountUp";
import { Reveal } from "../ui/Reveal";
import { EngineStatus } from "../layout/EngineStatus";
import { HouseScene } from "./HouseScene";

const REPO_URL = "https://github.com/quetinn/renosim";

export function Landing({ onOpenMethod }: { onOpenMethod: () => void }) {
  const { setView } = useAppState();
  const reduced = useReducedMotion();
  const heroRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: heroRef,
    offset: ["start start", "end start"],
  });
  const blobY = useTransform(scrollYProgress, [0, 1], [0, reduced ? 0 : 140]);
  const sceneY = useTransform(scrollYProgress, [0, 1], [0, reduced ? 0 : 60]);

  return (
    <div>
      {/* ── Hero ─────────────────────────────────────────────────────────── */}
      <section ref={heroRef} className="relative overflow-hidden">
        <motion.div
          aria-hidden
          style={{ y: blobY }}
          className="pointer-events-none absolute -top-32 -left-24 h-96 w-96 rounded-full bg-pine-soft blur-3xl animate-drift"
        />
        <motion.div
          aria-hidden
          style={{ y: blobY }}
          className="pointer-events-none absolute top-24 -right-32 h-[28rem] w-[28rem] rounded-full bg-amber-soft blur-3xl animate-drift"
        />

        <div className="relative mx-auto grid max-w-6xl items-center gap-10 px-4 pt-14 pb-16 sm:px-6 lg:grid-cols-[1.05fr_1fr] lg:pt-20 lg:pb-24">
          <div className="space-y-7">
            <motion.div
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, ease: [0.22, 0.65, 0.3, 1] }}
              className="space-y-7"
            >
              <span className="inline-flex items-center gap-2 rounded-full border border-line bg-surface px-4 py-1.5 text-xs font-semibold tracking-wide text-pine uppercase">
                <Sparkles size={14} aria-hidden />
                Simulateur ouvert & confronté aux données ADEME
              </span>
              <h1 className="font-display text-4xl leading-[1.08] font-semibold tracking-tight sm:text-5xl lg:text-6xl">
                Votre maison peut faire{" "}
                <span className="relative whitespace-nowrap text-pine">
                  beaucoup mieux
                  <svg
                    aria-hidden
                    viewBox="0 0 220 12"
                    className="absolute -bottom-2 left-0 w-full"
                    preserveAspectRatio="none"
                  >
                    <path
                      d="M3 9 Q60 2 110 6 T217 4"
                      fill="none"
                      stroke="var(--color-amber)"
                      strokeWidth="5"
                      strokeLinecap="round"
                    />
                  </svg>
                </span>
                .
              </h1>
              <p className="max-w-xl text-lg leading-relaxed text-ink-soft">
                Décrivez votre logement en deux minutes. RénoSim estime son étiquette DPE, montre
                par où part la chaleur, puis chiffre chaque geste de rénovation : coût, économies,
                CO₂ évité et temps de retour.
              </p>
              <div className="flex flex-wrap items-center gap-3">
                <Button size="lg" onClick={() => setView("form")}>
                  Simuler mon logement
                  <ArrowRight size={18} aria-hidden />
                </Button>
                <Button size="lg" variant="outline" onClick={onOpenMethod}>
                  <BookOpen size={17} aria-hidden />
                  Découvrir la méthode
                </Button>
              </div>
              <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-sm text-ink-soft">
                <span className="inline-flex items-center gap-1.5">
                  <ShieldCheck size={15} className="text-pine" aria-hidden />
                  Méthode 3CL-DPE 2021
                </span>
                <span className="inline-flex items-center gap-1.5">
                  <Lock size={15} className="text-pine" aria-hidden />
                  100 % dans votre navigateur
                </span>
                <EngineStatus />
              </div>
            </motion.div>
          </div>

          <motion.div
            style={{ y: sceneY }}
            initial={{ opacity: 0, scale: 0.94 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.7, delay: 0.15, ease: [0.22, 0.65, 0.3, 1] }}
            className="mx-auto w-full max-w-xl"
          >
            <HouseScene />
          </motion.div>
        </div>
      </section>

      {/* ── Validation stats ─────────────────────────────────────────────── */}
      <section className="border-y border-line bg-surface">
        <div className="mx-auto grid max-w-6xl gap-8 px-4 py-12 sm:grid-cols-3 sm:px-6">
          <Reveal className="text-center sm:text-left">
            <p className="font-display text-4xl font-semibold text-pine">
              <CountUp value={11496} />
            </p>
            <p className="mt-1 text-sm text-ink-soft">
              DPE officiels tirés au hasard dans la base ADEME, jamais utilisés pour régler le
              moteur
            </p>
          </Reveal>
          <Reveal delay={0.1} className="text-center sm:text-left">
            <p className="font-display text-4xl font-semibold text-pine">
              <CountUp value={87.0} format={(v) => `${v.toFixed(1).replace(".", ",")} %`} />
            </p>
            <p className="mt-1 text-sm text-ink-soft">
              d'étiquettes prédites à ±1 classe du diagnostic officiel (plus fiable pour le gaz,
              le fioul et les maisons de 1975 à 2012)
            </p>
          </Reveal>
          <Reveal delay={0.2} className="text-center sm:text-left">
            <p className="font-display text-4xl font-semibold text-pine">
              7 <span className="text-2xl">gestes</span>
            </p>
            <p className="mt-1 text-sm text-ink-soft">
              six pour la facture d'hiver, un pour le confort d'été, combinables en bouquets avec
              interactions calculées — pas de simple addition
            </p>
          </Reveal>
        </div>
      </section>

      {/* ── 3 steps ──────────────────────────────────────────────────────── */}
      <section className="mx-auto max-w-6xl px-4 py-20 sm:px-6">
        <Reveal>
          <h2 className="font-display text-3xl font-semibold sm:text-4xl">
            Trois étapes, zéro jargon
          </h2>
          <p className="mt-3 max-w-2xl text-ink-soft">
            Tous les champs techniques ont un défaut raisonnable déduit de l'année de
            construction : même pressé, vous obtenez un résultat fiable.
          </p>
        </Reveal>
        <div className="mt-10 grid gap-6 md:grid-cols-3">
          {[
            {
              icon: ClipboardList,
              step: "1",
              title: "Décrivez votre logement",
              text: "Code postal, surface, année, isolation, chauffage… Un parcours guidé de deux minutes, avec de l'aide à chaque question.",
            },
            {
              icon: Home,
              step: "2",
              title: "Comprenez votre situation",
              text: "Étiquette DPE estimée, décomposition des déperditions — par où part la chaleur — consommation, coût annuel et CO₂.",
            },
            {
              icon: Sparkles,
              step: "3",
              title: "Comparez les scénarios",
              text: "Activez des gestes ou des bouquets : coût des travaux en fourchette, économies annuelles, temps de retour et nouvelle étiquette.",
            },
          ].map(({ icon: Icon, step, title, text }, i) => (
            <Reveal key={step} delay={i * 0.12}>
              <div className="group relative h-full rounded-3xl border border-line bg-surface p-7 shadow-card transition-all duration-300 hover:-translate-y-1 hover:shadow-lift">
                <span
                  aria-hidden
                  className="absolute top-6 right-7 font-display text-5xl font-semibold text-cream select-none group-hover:text-pine-soft"
                >
                  {step}
                </span>
                <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-pine-soft text-pine">
                  <Icon size={22} aria-hidden />
                </span>
                <h3 className="mt-5 text-lg font-semibold">{title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-ink-soft">{text}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* ── Transparency ─────────────────────────────────────────────────── */}
      <section className="bg-pine-mist">
        <div className="mx-auto grid max-w-6xl gap-10 px-4 py-20 sm:px-6 lg:grid-cols-2 lg:items-center">
          <Reveal>
            <h2 className="font-display text-3xl font-semibold sm:text-4xl">
              Un moteur physique, pas une boîte noire
            </h2>
            <p className="mt-4 leading-relaxed text-ink-soft">
              Le calcul suit la méthode réglementaire 3CL-DPE 2021 dans une version simplifiée dont
              chaque écart est documenté. Le moteur, les tables de données sourcées et la campagne
              de validation contre la base ADEME sont publics : quiconque peut relire, tester et
              reproduire les résultats.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Button variant="outline" onClick={onOpenMethod}>
                <BookOpen size={16} aria-hidden />
                Hypothèses & limites
              </Button>
              <a
                href={REPO_URL}
                target="_blank"
                rel="noreferrer"
                className="inline-flex min-h-11 cursor-pointer items-center gap-2 rounded-full border border-line-strong bg-surface px-5 text-sm font-semibold text-ink transition-colors hover:border-pine hover:text-pine"
              >
                <Code size={16} aria-hidden />
                Code source ouvert
              </a>
            </div>
          </Reveal>
          <Reveal delay={0.15}>
            <div className="space-y-3">
              {[
                "Déperditions paroi par paroi, ponts thermiques et ventilation",
                "Besoins mensuels par degrés-heures, apports solaires et internes",
                "Rendements des systèmes selon leur type et leur âge",
                "Étiquette au double seuil énergie primaire / CO₂ du DPE 2021",
              ].map((line, i) => (
                <div
                  key={i}
                  className="flex items-start gap-3 rounded-2xl border border-line bg-surface px-5 py-4 text-sm shadow-card"
                >
                  <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-pine text-xs font-bold text-on-pine">
                    {i + 1}
                  </span>
                  <span className="text-ink-soft">{line}</span>
                </div>
              ))}
            </div>
          </Reveal>
        </div>
      </section>

      {/* ── Final CTA ────────────────────────────────────────────────────── */}
      <section className="relative overflow-hidden bg-pine-ink">
        <div
          aria-hidden
          className="pointer-events-none absolute -top-24 right-10 h-72 w-72 rounded-full bg-pine blur-3xl opacity-40 animate-drift"
        />
        <div className="relative mx-auto flex max-w-6xl flex-col items-start gap-6 px-4 py-16 sm:px-6 md:flex-row md:items-center md:justify-between">
          <div>
            <h2 className="font-display text-3xl font-semibold text-white sm:text-4xl">
              Deux minutes pour y voir clair.
            </h2>
            <p className="mt-2 max-w-xl text-sm leading-relaxed text-white/70">
              Outil pédagogique : il ne remplace ni un DPE officiel ni un audit énergétique. Pour
              les aides financières, consultez{" "}
              <a
                href="https://france-renov.gouv.fr"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 font-medium text-white underline decoration-white/40 underline-offset-2 hover:decoration-white"
              >
                France Rénov'
                <ExternalLink size={12} aria-hidden />
              </a>
              .
            </p>
          </div>
          <Button size="lg" variant="accent" onClick={() => setView("form")}>
            Commencer la simulation
            <ArrowRight size={18} aria-hidden />
          </Button>
        </div>
      </section>
    </div>
  );
}
