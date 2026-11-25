import { useState } from "react";
import { ArrowRight, Check } from "lucide-react";
import { MEASURE_LABELS } from "../../i18n/fr";
import { useAppState } from "../../state/AppState";
import type { EnvelopeBreakdown, MeasureType } from "../../types/schema";
import { Button } from "../ui/Button";

interface Zone {
  key: string;
  label: string;
  share: number; // % of total GV
  measure: MeasureType | null;
  hint: string;
}

/** Share → color: green (small loss) to red-orange (dominant loss), scaled to
 * the biggest zone so the map always uses the full ramp. */
function heatColor(share: number, maxShare: number): string {
  const t = maxShare > 0 ? Math.min(1, share / maxShare) : 0;
  const hue = 145 - 130 * t;
  return `hsl(${hue.toFixed(0)} 50% 45%)`;
}

/**
 * Interactive cross-section of the house (#13): each zone is colored by its
 * share of the heat-loss coefficient GV and, when a V1 renovation measure
 * matches, clicking toggles that measure for the scenarios screen.
 */
export function HouseLossMap({ envelope }: { envelope: EnvelopeBreakdown }) {
  const { activeMeasures, toggleMeasure, setView } = useAppState();
  const [lastToggled, setLastToggled] = useState<MeasureType | null>(null);

  const total = envelope.total_w_per_k;
  const pct = (v: number) => (total > 0 ? (v / total) * 100 : 0);
  const zones: Record<string, Zone> = {
    roof: {
      key: "roof",
      label: "Toiture",
      share: pct(envelope.roof_w_per_k),
      measure: "roof_insulation",
      hint: "cliquer pour isoler les combles",
    },
    walls: {
      key: "walls",
      label: "Murs",
      share: pct(envelope.walls_w_per_k),
      measure: "wall_insulation",
      hint: "cliquer pour isoler les murs",
    },
    windows: {
      key: "windows",
      label: "Fenêtres",
      share: pct(envelope.windows_w_per_k),
      measure: "window_replacement",
      hint: "cliquer pour changer les fenêtres",
    },
    floor: {
      key: "floor",
      label: "Plancher",
      share: pct(envelope.floor_w_per_k),
      measure: null,
      hint: "pas de geste plancher bas en V1",
    },
    air: {
      key: "air",
      label: "Air",
      share: pct(envelope.ventilation_w_per_k + envelope.infiltration_w_per_k),
      measure: "ventilation_upgrade",
      hint: "cliquer pour améliorer la ventilation",
    },
    bridges: {
      key: "bridges",
      label: "Ponts th.",
      share: pct(envelope.thermal_bridges_w_per_k),
      measure: null,
      hint: "traités par l'isolation des parois",
    },
  };
  const maxShare = Math.max(...Object.values(zones).map((z) => z.share));

  const fill = (z: Zone) => heatColor(z.share, maxShare);
  const isActive = (z: Zone) => z.measure !== null && activeMeasures.has(z.measure);

  const zoneProps = (z: Zone) => ({
    role: z.measure ? "button" : undefined,
    tabIndex: z.measure ? 0 : undefined,
    "aria-pressed": z.measure ? isActive(z) : undefined,
    "aria-label": `${z.label} : ${z.share.toFixed(0)} % des déperditions — ${z.hint}`,
    className: z.measure
      ? "cursor-pointer transition-opacity hover:opacity-80 focus:outline-none"
      : undefined,
    onClick: z.measure
      ? () => {
          toggleMeasure(z.measure as MeasureType);
          setLastToggled(z.measure);
        }
      : undefined,
    onKeyDown: z.measure
      ? (e: React.KeyboardEvent) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            toggleMeasure(z.measure as MeasureType);
            setLastToggled(z.measure);
          }
        }
      : undefined,
  });

  const label = (x: number, y: number, z: Zone, anchor: "start" | "middle" | "end" = "middle") => (
    <text
      x={x}
      y={y}
      textAnchor={anchor}
      className="pointer-events-none select-none"
      style={{
        fill: "var(--color-ink)",
        fontSize: 13,
        fontWeight: 700,
        paintOrder: "stroke",
        stroke: "var(--color-surface)",
        strokeWidth: 3.5,
        strokeLinejoin: "round",
      }}
    >
      {z.label} {z.share.toFixed(0)} %
    </text>
  );

  const activeOutline = (z: Zone) =>
    isActive(z) ? { stroke: "var(--color-pine)", strokeWidth: 3.5, strokeDasharray: "7 4" } : {};

  return (
    <div>
      <svg
        viewBox="0 0 480 372"
        role="group"
        aria-label="Coupe de la maison colorée selon la part de chaque zone dans les déperditions ; les zones couvertes par un geste de rénovation sont cliquables."
        className="mx-auto block w-full max-w-md"
      >
        {/* Ground */}
        <line x1="18" y1="346" x2="462" y2="346" stroke="var(--color-line-strong)" strokeWidth="2.5" />

        {/* Floor slab (informative) */}
        <g {...zoneProps(zones.floor)}>
          <title>{`Plancher bas : ${zones.floor.share.toFixed(0)} % — ${zones.floor.hint}`}</title>
          <rect x="118" y="322" width="244" height="20" rx="4" fill={fill(zones.floor)} />
        </g>

        {/* Interior */}
        <rect x="136" y="168" width="208" height="154" fill="var(--color-cream)" />

        {/* Walls: two posts + lintel band */}
        <g {...zoneProps(zones.walls)}>
          <rect x="118" y="168" width="18" height="154" fill={fill(zones.walls)} {...activeOutline(zones.walls)} />
          <rect x="344" y="168" width="18" height="154" fill={fill(zones.walls)} {...activeOutline(zones.walls)} />
        </g>

        {/* Roof */}
        <g {...zoneProps(zones.roof)}>
          <polygon
            points="96,172 240,58 384,172"
            fill={fill(zones.roof)}
            {...activeOutline(zones.roof)}
          />
        </g>
        {/* Attic mask so the roof reads as a band, not a filled gable */}
        <polygon points="136,168 240,86 344,168" fill="var(--color-surface)" opacity="0.55" />

        {/* Windows */}
        <g {...zoneProps(zones.windows)}>
          <rect x="162" y="208" width="56" height="66" rx="4" fill={fill(zones.windows)} {...activeOutline(zones.windows)} />
          <rect x="262" y="208" width="56" height="66" rx="4" fill={fill(zones.windows)} {...activeOutline(zones.windows)} />
          {/* window crosses */}
          <line x1="190" y1="208" x2="190" y2="274" stroke="var(--color-surface)" strokeWidth="2.5" />
          <line x1="290" y1="208" x2="290" y2="274" stroke="var(--color-surface)" strokeWidth="2.5" />
        </g>

        {/* Air renewal: vent stack + escaping arrows */}
        <g {...zoneProps(zones.air)}>
          <rect x="292" y="72" width="20" height="44" rx="3" fill={fill(zones.air)} {...activeOutline(zones.air)} />
          <g stroke={fill(zones.air)} strokeWidth="3" fill="none" strokeLinecap="round">
            <path d="M302 62 q -5 -10 2 -20" />
            <path d="M312 66 q 6 -12 -1 -24" />
          </g>
        </g>

        {/* Thermal bridges: junction markers (informative) */}
        <g {...zoneProps(zones.bridges)}>
          <title>{`Ponts thermiques : ${zones.bridges.share.toFixed(0)} % — ${zones.bridges.hint}`}</title>
          <circle cx="127" cy="322" r="7" fill={fill(zones.bridges)} />
          <circle cx="353" cy="322" r="7" fill={fill(zones.bridges)} />
          <circle cx="127" cy="172" r="7" fill={fill(zones.bridges)} />
          <circle cx="353" cy="172" r="7" fill={fill(zones.bridges)} />
        </g>

        {/* Labels */}
        {label(240, 130, zones.roof)}
        {label(108, 250, zones.walls, "end")}
        {label(240, 300, zones.windows)}
        {label(240, 366, zones.floor)}
        {label(330, 46, zones.air, "start")}
        {label(372, 316, zones.bridges, "start")}
      </svg>

      <p className="mt-2 text-center text-xs leading-relaxed text-ink-faint">
        Du vert (faible) au rouge (dominant) : la part de chaque zone dans les déperditions.
        Cliquez sur une zone pour activer le geste de rénovation correspondant.
      </p>

      {lastToggled && (
        <p className="mt-3 flex flex-wrap items-center justify-center gap-2 text-sm">
          <span className="inline-flex items-center gap-1.5 font-medium text-pine">
            <Check size={15} aria-hidden />
            {MEASURE_LABELS[lastToggled].title} —{" "}
            {activeMeasures.has(lastToggled) ? "geste activé" : "geste désactivé"}
          </span>
          {activeMeasures.size > 0 && (
            <Button variant="outline" onClick={() => setView("scenarios")}>
              Voir l'impact dans mes scénarios
              <ArrowRight size={15} aria-hidden />
            </Button>
          )}
        </p>
      )}
    </div>
  );
}
