import { motion, useReducedMotion } from "motion/react";
import { DPE_CLASS_DESCRIPTIONS } from "../../i18n/fr";
import type { DpeClass } from "../../types/schema";
import { formatInt } from "../../utils/format";

export const DPE_COLORS: Record<DpeClass, string> = {
  A: "var(--color-dpe-a)",
  B: "var(--color-dpe-b)",
  C: "var(--color-dpe-c)",
  D: "var(--color-dpe-d)",
  E: "var(--color-dpe-e)",
  F: "var(--color-dpe-f)",
  G: "var(--color-dpe-g)",
};

/** Dark text is needed on the light C/D swatches for contrast. */
const DARK_TEXT: DpeClass[] = ["C", "D"];

const CLASSES: DpeClass[] = ["A", "B", "C", "D", "E", "F", "G"];

/**
 * DPE ladder following the official label layout: growing colored arrows,
 * the current class enlarged with the kWhep value alongside.
 */
export function DpeScale({
  label,
  cepKwhepM2,
  gesKgM2,
}: {
  label: DpeClass;
  cepKwhepM2: number;
  gesKgM2: number;
}) {
  const reduced = useReducedMotion();
  return (
    <div className="space-y-1.5" role="img" aria-label={`Étiquette DPE estimée : classe ${label}, ${formatInt(cepKwhepM2)} kilowattheures d'énergie primaire par mètre carré et par an, ${formatInt(gesKgM2)} kilogrammes de CO2 par mètre carré et par an.`}>
      {CLASSES.map((cls, i) => {
        const active = cls === label;
        const width = 34 + i * 9;
        return (
          <div key={cls} className="flex items-center gap-3">
            <motion.div
              initial={reduced ? false : { width: 0, opacity: 0 }}
              animate={{ width: `${active ? width + 14 : width}%`, opacity: 1 }}
              transition={{ delay: reduced ? 0 : 0.06 * i, duration: 0.45, ease: "easeOut" }}
              className={`relative flex h-9 min-w-14 items-center rounded-l-md px-3 ${
                active ? "shadow-lift" : ""
              }`}
              style={{
                background: DPE_COLORS[cls],
                opacity: active ? 1 : 0.4,
                clipPath: "polygon(0 0, calc(100% - 14px) 0, 100% 50%, calc(100% - 14px) 100%, 0 100%)",
              }}
            >
              <span
                className={`text-base font-extrabold ${
                  DARK_TEXT.includes(cls) ? "text-ink" : "text-white"
                }`}
              >
                {cls}
              </span>
            </motion.div>
            {active && (
              <motion.div
                initial={reduced ? false : { opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: reduced ? 0 : 0.55, duration: 0.3 }}
                className="whitespace-nowrap"
              >
                <span className="text-lg font-bold tabular">{formatInt(cepKwhepM2)}</span>
                <span className="ml-1 text-xs text-ink-faint">kWhep/m²·an</span>
              </motion.div>
            )}
          </div>
        );
      })}
      <p className="pt-2 text-sm font-medium text-ink-soft">
        Classe {label} — {DPE_CLASS_DESCRIPTIONS[label]}
      </p>
    </div>
  );
}

/** Small colored badge used in comparison tables. */
export function DpeBadge({ label, size = "md" }: { label: DpeClass; size?: "md" | "lg" }) {
  return (
    <span
      className={`inline-flex items-center justify-center rounded-lg font-extrabold ${
        DARK_TEXT.includes(label) ? "text-ink" : "text-white"
      } ${size === "lg" ? "h-10 w-10 text-lg" : "h-8 w-8 text-sm"}`}
      style={{ background: DPE_COLORS[label] }}
    >
      {label}
    </span>
  );
}
