/**
 * Formatting helpers. Kept separate from data sources so mock data can be
 * replaced with API data without rewriting the UI (OVERVIEW.md §9.6).
 *
 * All formatters use a fixed "en-US" locale and UTC to keep server/client
 * output deterministic (avoids hydration mismatches). Currency is USD for
 * this prototype (team decision).
 */

const LOCALE = "en-US";
const CURRENCY = "USD";

export function formatCurrency(
  value: number,
  options: { decimals?: number; sign?: boolean } = {},
): string {
  const { decimals = 0, sign = false } = options;
  const formatted = new Intl.NumberFormat(LOCALE, {
    style: "currency",
    currency: CURRENCY,
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(Math.abs(value));
  if (sign) return `${value >= 0 ? "+" : "-"}${formatted}`;
  return value < 0 ? `-${formatted}` : formatted;
}

export function formatNumber(
  value: number,
  options: { decimals?: number; sign?: boolean } = {},
): string {
  const { decimals = 0, sign = false } = options;
  const formatted = new Intl.NumberFormat(LOCALE, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(Math.abs(value));
  if (sign) return `${value >= 0 ? "+" : "-"}${formatted}`;
  return value < 0 ? `-${formatted}` : formatted;
}

export function formatPercent(
  value: number,
  options: { decimals?: number; sign?: boolean } = {},
): string {
  const { decimals = 1, sign = false } = options;
  const formatted = `${value.toFixed(decimals)}%`;
  if (sign) return `${value >= 0 ? "+" : "-"}${value.toFixed(decimals)}%`;
  return value < 0 ? `-${formatted}` : formatted;
}

export function formatMonthYear(iso: string): string {
  const date = new Date(`${iso}T00:00:00Z`);
  return new Intl.DateTimeFormat(LOCALE, {
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  }).format(date);
}

export function formatShortMonthYear(iso: string): string {
  const date = new Date(`${iso}T00:00:00Z`);
  return new Intl.DateTimeFormat(LOCALE, {
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(date);
}

export function formatDateNumeric(iso: string): string {
  const date = new Date(`${iso}T00:00:00Z`);
  return new Intl.DateTimeFormat(LOCALE, {
    month: "2-digit",
    day: "2-digit",
    year: "numeric",
    timeZone: "UTC",
  }).format(date);
}

export function progressPct(current: number, target: number): number {
  if (target <= 0) return 0;
  return Math.max(0, Math.min(100, (current / target) * 100));
}
