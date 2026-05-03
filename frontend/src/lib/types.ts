/**
 * Backend response shapes for the GovLink REST API.
 *
 * Source of truth: `backend/docs/api-reference.md` and `backend/CLAUDE.md`.
 * Keep this file in sync with backend changes.
 */

export type Frequency =
  | "daily"
  | "weekly"
  | "monthly"
  | "quarterly"
  | "annual"
  | "irregular";

export interface MetaEnvelope {
  dataset?: string;
  count: number;
  total?: number | null;
  limit?: number | null;
  offset?: number | null;
  /** YYYY-MM-DD; only present on /latest */
  snapshot_date?: string | null;
  /** ISO-8601 UTC */
  generated_at: string;
}

export interface Envelope<T> {
  data: T;
  meta: MetaEnvelope;
}

export interface ApiErrorEnvelope {
  error: {
    code: string;
    message: string;
    details?: unknown;
  };
}

/* ---------- Datasets ---------- */

export interface DatasetSummary {
  slug: string;
  title: string;
  description: string;
  publisher: string;
  source_url: string;
  frequency: Frequency;
}

export interface DatasetField {
  name: string;
  /** Backend serializes Python type repr — e.g. "<class 'datetime.date'>" */
  type: string;
}

export interface DatasetDetail extends DatasetSummary {
  data_table_name: string;
  fields: DatasetField[];
}

/**
 * One row of dataset data. Generic record because the schema is dynamic
 * per dataset. Decimal values arrive as strings (DecimalStr — see
 * CLAUDE.md §1: never `Number(...)` them).
 */
export type DatasetRecord = Record<string, string | number | boolean | null>;

/* ---------- Operator health ---------- */

export interface DatasetHealth {
  slug: string;
  frequency: Frequency;
  /** ISO-8601 UTC, or null if never ingested */
  last_ingested_at: string | null;
  /** YYYY-MM-DD, or null if no rows */
  latest_snapshot_date: string | null;
  is_stale: boolean;
}

export interface HealthResponse {
  datasets: DatasetHealth[];
  count: number;
}

/* ---------- Query parameter helpers ---------- */

export interface HistoricalParams {
  /** YYYY-MM-DD */
  from?: string;
  /** YYYY-MM-DD */
  to?: string;
  currency?: string;
  /** 1–1000, default 100 */
  limit?: number;
  /** ≥0, default 0 */
  offset?: number;
}
