import {
  CartesianGrid,
  Cell,
  LabelList,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatEuros, formatInt } from "../../utils/format";

export interface CostGainPoint {
  id: string;
  name: string;
  investment: number;
  savings: number;
  bouquet: boolean;
}

/** Scatter "coût vs gain" — one point per scenario (lazy-loaded, recharts chunk). */
export default function CostGainChart({ points }: { points: CostGainPoint[] }) {
  return (
    <ResponsiveContainer width="100%" height={320}>
      <ScatterChart margin={{ top: 28, right: 36, bottom: 12, left: 8 }}>
        <CartesianGrid stroke="var(--color-line)" strokeDasharray="4 6" />
        <XAxis
          type="number"
          dataKey="investment"
          name="Investissement"
          tickFormatter={(v) => `${formatInt((v as number) / 1000)} k€`}
          label={{
            value: "Investissement (milieu de fourchette)",
            position: "insideBottom",
            offset: -6,
            style: { fill: "var(--color-ink-faint)", fontSize: 12 },
          }}
        />
        <YAxis
          type="number"
          dataKey="savings"
          name="Économies"
          tickFormatter={(v) => `${formatInt(v as number)} €`}
          label={{
            value: "Économies (€/an)",
            angle: -90,
            position: "insideLeft",
            style: { fill: "var(--color-ink-faint)", fontSize: 12 },
          }}
        />
        <Tooltip
          cursor={{ strokeDasharray: "4 4" }}
          contentStyle={{
            background: "var(--color-surface)",
            border: "1px solid var(--color-line)",
            borderRadius: 12,
            color: "var(--color-ink)",
          }}
          formatter={(value, name) => [
            name === "Investissement"
              ? formatEuros(value as number)
              : `${formatEuros(value as number)}/an`,
            name,
          ]}
        />
        <Scatter data={points} isAnimationActive={false}>
          {points.map((p) => (
            <Cell
              key={p.id}
              fill={p.bouquet ? "var(--color-amber)" : "var(--color-pine)"}
              r={p.bouquet ? 10 : 7}
            />
          ))}
          <LabelList
            dataKey="name"
            position="top"
            style={{ fill: "var(--color-ink-soft)", fontSize: 11, fontWeight: 600 }}
          />
        </Scatter>
      </ScatterChart>
    </ResponsiveContainer>
  );
}
