import { useMemo } from "react";
import type { DatasetRecord } from "@/lib/types";
import { cn } from "@/lib/utils";
import { formatDate, formatDecimalStr } from "@/lib/format";

interface DataTableProps {
  rows: DatasetRecord[];
  /** Optional explicit column order; defaults to keys from row[0]. */
  columns?: string[];
  /** Field name → friendly header. */
  labels?: Record<string, string>;
  className?: string;
}

/**
 * Newspaper-style data table — rule lines top + bottom, hairline between
 * rows, no zebra striping, tabular numerals throughout (per brand-spec).
 *
 * Right-aligns columns whose values all look numeric. Auto-formats
 * `*_date` columns through formatDate, and decimal strings preserved
 * via formatDecimalStr (no float coercion — DecimalStr stays exact).
 */
export function DataTable({
  rows,
  columns,
  labels = {},
  className,
}: DataTableProps) {
  const cols = useMemo(() => {
    if (columns && columns.length > 0) return columns;
    if (rows.length === 0) return [];
    return Object.keys(rows[0]);
  }, [columns, rows]);

  const isNumericCol = useMemo(
    () =>
      Object.fromEntries(
        cols.map((c) => [
          c,
          rows.length > 0 &&
            rows.every(
              (r) =>
                r[c] === null ||
                r[c] === undefined ||
                isNumericValue(r[c] as string | number),
            ),
        ]),
      ),
    [cols, rows],
  );

  if (rows.length === 0) {
    return (
      <p className="rounded-lg border border-dashed border-rule px-6 py-10 text-center text-sm text-ink-3">
        No rows.
      </p>
    );
  }

  return (
    <div className={cn("overflow-x-auto rounded-lg border border-rule bg-surface", className)}>
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b border-rule text-[10px] font-semibold uppercase tracking-[0.12em] text-ink-3">
            {cols.map((c) => (
              <th
                key={c}
                scope="col"
                className={cn(
                  "px-4 py-3 font-semibold",
                  isNumericCol[c] ? "text-right" : "text-left",
                )}
              >
                {labels[c] ?? prettify(c)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr
              key={i}
              className="border-b border-rule last:border-b-0 transition-colors duration-2 ease hover:bg-accent-tint/40"
            >
              {cols.map((c) => (
                <td
                  key={c}
                  className={cn(
                    "px-4 py-3 align-top",
                    isNumericCol[c] ? "text-right" : "text-left",
                  )}
                >
                  {formatCell(c, row[c])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function prettify(key: string): string {
  return key
    .split("_")
    .map((s) => s.charAt(0).toUpperCase() + s.slice(1))
    .join(" ");
}

function isNumericValue(v: unknown): boolean {
  if (typeof v === "number") return Number.isFinite(v);
  if (typeof v !== "string") return false;
  return /^-?\d+(\.\d+)?$/.test(v.trim());
}

function formatCell(key: string, value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";

  // Date columns — backend uses YYYY-MM-DD on snapshot_date and friends.
  if (/(^|_)date($|_)/.test(key)) {
    return formatDate(String(value));
  }

  // Decimal strings — preserve exact precision per CLAUDE.md §1.
  if (typeof value === "string" && /^-?\d+\.\d+$/.test(value)) {
    return formatDecimalStr(value);
  }

  return String(value);
}
