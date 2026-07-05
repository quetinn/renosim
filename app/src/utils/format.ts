/** French-locale display formatting. Display only — never business logic. */

const nf0 = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 });
const nf1 = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 1, minimumFractionDigits: 1 });

export function formatInt(value: number): string {
  return nf0.format(Math.round(value));
}

export function formatOneDecimal(value: number): string {
  return nf1.format(value);
}

export function formatEuros(value: number): string {
  return `${nf0.format(Math.round(value))} €`;
}

export function formatEuroRange(low: number, high: number): string {
  return `${nf0.format(Math.round(low))} – ${nf0.format(Math.round(high))} €`;
}

/** Simple payback, displayed "> 30 ans" beyond the brief's threshold (§4.4). */
export function formatPayback(years: number | null): string {
  if (years === null || years > 30) return "> 30 ans";
  if (years < 1) return "< 1 an";
  return `${nf0.format(Math.round(years))} ans`;
}

export function formatKwh(value: number): string {
  return `${nf0.format(Math.round(value))} kWh`;
}

export function formatKgCo2(value: number): string {
  const abs = Math.abs(value);
  if (abs >= 1000) return `${nf1.format(value / 1000)} t CO₂`;
  return `${nf0.format(Math.round(value))} kg CO₂`;
}
