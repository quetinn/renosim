import type { ReactNode } from "react";
import { InfoTip } from "../ui/InfoTip";

export function Field({
  label,
  help,
  children,
}: {
  label: string;
  help?: string;
  children: ReactNode;
}) {
  return (
    <div className="space-y-2.5">
      <div className="flex items-center gap-1.5">
        <span className="text-sm font-semibold text-ink">{label}</span>
        {help && <InfoTip text={help} />}
      </div>
      {children}
    </div>
  );
}

export interface Option<T extends string> {
  value: T;
  label: string;
  hint?: string;
}

/** Radio-card group: large touch targets, visible selected state. */
export function RadioCards<T extends string>({
  name,
  options,
  value,
  onChange,
  columns = 2,
}: {
  name: string;
  options: Option<T>[];
  value: T;
  onChange: (value: T) => void;
  columns?: 1 | 2 | 3;
}) {
  const cols = { 1: "grid-cols-1", 2: "grid-cols-1 sm:grid-cols-2", 3: "grid-cols-1 sm:grid-cols-3" }[
    columns
  ];
  return (
    <div role="radiogroup" aria-label={name} className={`grid gap-2.5 ${cols}`}>
      {options.map((opt) => {
        const selected = opt.value === value;
        return (
          <button
            key={opt.value}
            type="button"
            role="radio"
            aria-checked={selected}
            onClick={() => onChange(opt.value)}
            className={`min-h-11 cursor-pointer rounded-2xl border px-4 py-3 text-left transition-all duration-200 ${
              selected
                ? "border-pine bg-pine-soft shadow-card"
                : "border-line bg-surface hover:border-line-strong"
            }`}
          >
            <span className={`block text-sm font-medium ${selected ? "text-pine-deep" : "text-ink"}`}>
              {opt.label}
            </span>
            {opt.hint && <span className="mt-0.5 block text-xs text-ink-faint">{opt.hint}</span>}
          </button>
        );
      })}
    </div>
  );
}

/** Compact segmented control for short option lists. */
export function Segmented<T extends string>({
  name,
  options,
  value,
  onChange,
}: {
  name: string;
  options: Option<T>[];
  value: T;
  onChange: (value: T) => void;
}) {
  return (
    <div
      role="radiogroup"
      aria-label={name}
      className="inline-flex flex-wrap gap-1 rounded-full border border-line bg-surface p-1"
    >
      {options.map((opt) => {
        const selected = opt.value === value;
        return (
          <button
            key={opt.value}
            type="button"
            role="radio"
            aria-checked={selected}
            onClick={() => onChange(opt.value)}
            className={`min-h-9 cursor-pointer rounded-full px-4 py-1.5 text-sm font-medium transition-all duration-200 ${
              selected ? "bg-pine text-white shadow-card" : "text-ink-soft hover:text-ink"
            }`}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}

export function NumberInput({
  id,
  value,
  onChange,
  min,
  max,
  step = 1,
  suffix,
  ariaLabel,
}: {
  id?: string;
  value: number;
  onChange: (value: number) => void;
  min: number;
  max: number;
  step?: number;
  suffix?: string;
  ariaLabel?: string;
}) {
  return (
    <div className="inline-flex items-center gap-2 rounded-2xl border border-line bg-surface px-4 py-2 focus-within:border-pine">
      <input
        id={id}
        type="number"
        inputMode="decimal"
        value={Number.isFinite(value) ? value : ""}
        min={min}
        max={max}
        step={step}
        aria-label={ariaLabel}
        onChange={(e) => {
          const v = Number(e.target.value);
          if (!Number.isNaN(v)) onChange(v);
        }}
        className="w-24 border-none bg-transparent text-base font-semibold text-ink outline-none tabular"
      />
      {suffix && <span className="text-sm text-ink-faint">{suffix}</span>}
    </div>
  );
}
