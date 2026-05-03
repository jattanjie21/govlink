/**
 * Display formatters. Brand spec mandates `DD MMM YYYY` for dates and
 * tabular numerals for numbers — these helpers stay consistent with that.
 */

const MONTHS = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
] as const;

/**
 * Format a `YYYY-MM-DD` date string (backend `snapshot_date`) or any
 * value parseable by `new Date(...)` as `DD MMM YYYY` per brand spec.
 *
 * Returns "—" when the input is null/undefined/invalid so tables stay
 * aligned without conditional rendering at every cell.
 */
export function formatDate(input: string | Date | null | undefined): string {
  if (input == null) return "—";
  const d = typeof input === "string" ? parseFlexibleDate(input) : input;
  if (!d || isNaN(d.getTime())) return "—";
  const day = String(d.getUTCDate()).padStart(2, "0");
  return `${day} ${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
}

/**
 * `DD MMM YYYY · HH:MM UTC` — for `last_ingested_at`, `generated_at`.
 */
export function formatDateTime(input: string | Date | null | undefined): string {
  if (input == null) return "—";
  const d = typeof input === "string" ? new Date(input) : input;
  if (!d || isNaN(d.getTime())) return "—";
  const datePart = formatDate(d);
  const hours = String(d.getUTCHours()).padStart(2, "0");
  const minutes = String(d.getUTCMinutes()).padStart(2, "0");
  return `${datePart} · ${hours}:${minutes} UTC`;
}

/**
 * "3 hours ago" / "in 5 minutes" — uses Intl.RelativeTimeFormat.
 */
export function formatRelativeTime(
  input: string | Date | null | undefined,
  now: Date = new Date(),
): string {
  if (input == null) return "—";
  const d = typeof input === "string" ? new Date(input) : input;
  if (!d || isNaN(d.getTime())) return "—";

  const diffMs = d.getTime() - now.getTime();
  const diffSec = Math.round(diffMs / 1000);
  const abs = Math.abs(diffSec);

  const rtf = new Intl.RelativeTimeFormat("en", { numeric: "auto" });
  if (abs < 60) return rtf.format(diffSec, "second");
  if (abs < 3600) return rtf.format(Math.round(diffSec / 60), "minute");
  if (abs < 86400) return rtf.format(Math.round(diffSec / 3600), "hour");
  if (abs < 2592000) return rtf.format(Math.round(diffSec / 86400), "day");
  if (abs < 31536000) return rtf.format(Math.round(diffSec / 2592000), "month");
  return rtf.format(Math.round(diffSec / 31536000), "year");
}

/**
 * Format a `DecimalStr` (string from the backend like "1132.65") for
 * display. Preserves all significant digits — does NOT round.
 *
 * - Optionally adds thousands separators
 * - Pads/preserves trailing zeros on `minFractionDigits`
 * - Returns the input unchanged if it isn't a parseable decimal
 *   (so "—" or "N/A" pass through if a caller pre-formatted)
 */
export function formatDecimalStr(
  value: string | number | null | undefined,
  opts: { thousands?: boolean; minFractionDigits?: number } = {},
): string {
  if (value == null) return "—";
  const s = String(value).trim();
  if (!s) return "—";
  if (!/^-?\d+(\.\d+)?$/.test(s)) return s;

  const negative = s.startsWith("-");
  const body = negative ? s.slice(1) : s;
  const dot = body.indexOf(".");
  let intPart = dot === -1 ? body : body.slice(0, dot);
  let fracPart = dot === -1 ? "" : body.slice(dot + 1);

  if (opts.minFractionDigits !== undefined && fracPart.length < opts.minFractionDigits) {
    fracPart = fracPart.padEnd(opts.minFractionDigits, "0");
  }

  if (opts.thousands) {
    intPart = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  }

  const out = fracPart ? `${intPart}.${fracPart}` : intPart;
  return negative ? `-${out}` : out;
}

/**
 * Format a `frequency` enum value as Title Case — "daily" → "Daily".
 */
export function formatFrequency(f: string | null | undefined): string {
  if (!f) return "—";
  return f.charAt(0).toUpperCase() + f.slice(1);
}

/**
 * Internal — accept either `YYYY-MM-DD` or any Date-parseable string.
 * Treats `YYYY-MM-DD` as UTC so display doesn't shift in negative TZs.
 */
function parseFlexibleDate(s: string): Date | null {
  const ymd = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s);
  if (ymd) {
    return new Date(Date.UTC(Number(ymd[1]), Number(ymd[2]) - 1, Number(ymd[3])));
  }
  const d = new Date(s);
  return isNaN(d.getTime()) ? null : d;
}
