const isNum = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);

export const pct = (v: unknown, digits = 1) => (isNum(v) ? `${(v * 100).toFixed(digits)}%` : "–");

export const num = (v: unknown, digits = 0) =>
  isNum(v) ? v.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits }) : "–";

/** 1,284 / 12.9K / 4.2M / 1.3B */
export function compact(v: unknown, digits = 1): string {
  if (!isNum(v)) return "–";
  const a = Math.abs(v);
  if (a >= 1e9) return `${(v / 1e9).toFixed(digits)}B`;
  if (a >= 1e6) return `${(v / 1e6).toFixed(digits)}M`;
  if (a >= 1e4) return `${(v / 1e3).toFixed(digits)}K`;
  return num(v, 0);
}

export function byKind(kind: string, v: unknown): string {
  switch (kind) {
    case "percent":
      return pct(v, 1);
    case "count":
      return num(v);
    case "money":
      return compact(v);
    default:
      return isNum(v) ? v.toFixed(3) : "–";
  }
}

/** Title-case the all-caps weekday members etc. for display only. */
export const label = (s: string) => (/^[A-Z]{3,}$/.test(s) ? s[0] + s.slice(1).toLowerCase() : s);
