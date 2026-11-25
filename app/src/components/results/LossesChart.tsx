import {
  Bar,
  BarChart,
  Cell,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { LOSS_LABELS } from "../../i18n/fr";
import type { EnvelopeBreakdown } from "../../types/schema";

// Theme tokens (index.css) so the ramp adapts to the dark palette.
const COLORS: Record<string, string> = {
  walls: "var(--color-loss-walls)",
  roof: "var(--color-loss-roof)",
  windows: "var(--color-loss-windows)",
  floor: "var(--color-loss-floor)",
  thermal_bridges: "var(--color-loss-bridges)",
  ventilation: "var(--color-loss-ventilation)",
  infiltration: "var(--color-loss-infiltration)",
};

/** "Par où part la chaleur ?" — share of each loss path in the total GV
 * (default export: lazy-loaded so recharts stays in its own chunk). */
export default function LossesChart({ envelope }: { envelope: EnvelopeBreakdown }) {
  const entries = [
    ["walls", envelope.walls_w_per_k],
    ["roof", envelope.roof_w_per_k],
    ["windows", envelope.windows_w_per_k],
    ["floor", envelope.floor_w_per_k],
    ["thermal_bridges", envelope.thermal_bridges_w_per_k],
    ["ventilation", envelope.ventilation_w_per_k],
    ["infiltration", envelope.infiltration_w_per_k],
  ] as const;
  const total = envelope.total_w_per_k;
  const data = entries
    .map(([key, value]) => ({
      key,
      name: LOSS_LABELS[key],
      share: (value / total) * 100,
    }))
    .sort((a, b) => b.share - a.share);

  return (
    <div>
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={data} layout="vertical" margin={{ left: 8, right: 44, top: 4 }}>
          <XAxis type="number" hide domain={[0, "dataMax"]} />
          <YAxis
            type="category"
            dataKey="name"
            width={118}
            axisLine={false}
            tickLine={false}
            tick={{ fontSize: 13 }}
          />
          <Tooltip
            cursor={{ fill: "var(--color-cream)" }}
            contentStyle={{
              background: "var(--color-surface)",
              border: "1px solid var(--color-line)",
              borderRadius: 12,
              color: "var(--color-ink)",
            }}
            formatter={(value) => [`${(value as number).toFixed(1).replace(".", ",")} %`, "Part des pertes"]}
          />
          <Bar dataKey="share" radius={[0, 8, 8, 0]} isAnimationActive={false} barSize={22}>
            {data.map((d) => (
              <Cell key={d.key} fill={COLORS[d.key]} />
            ))}
            <LabelList
              dataKey="share"
              position="right"
              formatter={(v) => `${Number(v).toFixed(0)} %`}
              className="tabular"
              style={{ fill: "var(--color-ink-soft)", fontSize: 12, fontWeight: 600 }}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      {/* Screen-reader table alternative */}
      <table className="sr-only">
        <caption>Répartition des déperditions de chaleur</caption>
        <tbody>
          {data.map((d) => (
            <tr key={d.key}>
              <th scope="row">{d.name}</th>
              <td>{d.share.toFixed(0)} %</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
