import { Link } from "react-router-dom";
import { ArrowUpRight, RefreshCw } from "lucide-react";
import { Container } from "@/components/Container";
import { Eyebrow } from "@/components/Eyebrow";
import { EmptyState, ErrorState } from "@/components/States";
import { useHealth } from "@/lib/queries";
import {
  formatDate,
  formatDateTime,
  formatFrequency,
  formatRelativeTime,
} from "@/lib/format";
import { cn } from "@/lib/utils";
import type { DatasetHealth } from "@/lib/types";

export default function Operator() {
  const { data, isLoading, isError, error, isFetching, dataUpdatedAt, refetch } =
    useHealth(30_000);

  const total = data?.datasets.length ?? 0;
  const stale = data?.datasets.filter((d) => d.is_stale).length ?? 0;
  const fresh = total - stale;

  return (
    <>
      <section className="border-b border-rule pb-10 pt-12 md:pt-16">
        <Container>
          <div className="flex flex-wrap items-end justify-between gap-6">
            <div>
              <Eyebrow>Operator</Eyebrow>
              <h1 className="mt-6 font-display text-xl font-normal leading-tight tracking-tight">
                Dataset health
              </h1>
              <p className="mt-3 max-w-prose text-sm text-ink-2">
                Per-dataset freshness, sourced from{" "}
                <code className="font-mono text-xs text-ink">/admin/health</code>.
                Auto-refreshes every 30s.
              </p>
            </div>

            <div className="flex items-center gap-3 text-xs text-ink-3">
              <span className="num">
                Last refresh{" "}
                <span className="text-ink-2">
                  {dataUpdatedAt ? formatRelativeTime(new Date(dataUpdatedAt)) : "—"}
                </span>
              </span>
              <button
                type="button"
                onClick={() => refetch()}
                disabled={isFetching}
                className="inline-flex items-center gap-1.5 rounded border border-rule px-3 py-1.5 text-xs transition-colors duration-2 ease hover:border-rule-2 hover:bg-accent-tint disabled:opacity-60"
              >
                <RefreshCw
                  className={cn("h-3 w-3", isFetching && "animate-spin")}
                />
                Refresh
              </button>
            </div>
          </div>

          {/* KPI strip */}
          <dl className="mt-8 grid grid-cols-2 gap-x-8 gap-y-4 border-t border-rule pt-6 sm:grid-cols-3">
            <Kpi label="Datasets tracked" value={total} />
            <Kpi label="Fresh" value={fresh} accent="success" />
            <Kpi label="Stale" value={stale} accent={stale > 0 ? "warning" : "muted"} />
          </dl>
        </Container>
      </section>

      <section className="py-10">
        <Container>
          {isLoading && <LoadingHealthGrid />}
          {isError && (
            <ErrorState error={error} context="GET /admin/health" />
          )}
          {!isLoading && !isError && data && data.datasets.length === 0 && (
            <EmptyState
              title="No datasets registered yet"
              description="Once a dataset plugin is registered in the backend, it will appear here."
            />
          )}
          {data && data.datasets.length > 0 && (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
              {data.datasets.map((d) => (
                <HealthCard key={d.slug} dataset={d} />
              ))}
            </div>
          )}
        </Container>
      </section>
    </>
  );
}

function Kpi({
  label,
  value,
  accent = "muted",
}: {
  label: string;
  value: number;
  accent?: "muted" | "success" | "warning";
}) {
  return (
    <div>
      <dt className="text-[10px] font-semibold uppercase tracking-[0.12em] text-ink-3">
        {label}
      </dt>
      <dd
        className={cn(
          "mt-1.5 font-display text-xl font-normal num leading-none",
          accent === "success" && "text-success",
          accent === "warning" && "text-warning",
        )}
      >
        {value}
      </dd>
    </div>
  );
}

function HealthCard({ dataset }: { dataset: DatasetHealth }) {
  const { is_stale, slug, frequency, last_ingested_at, latest_snapshot_date } =
    dataset;

  return (
    <article className="flex flex-col rounded-lg border border-rule bg-surface">
      <header className="flex items-center justify-between border-b border-rule px-5 py-3">
        <Link
          to={`/datasets/${slug}`}
          className="group inline-flex items-center gap-1 font-mono text-xs text-ink hover:text-accent"
        >
          {slug}
          <ArrowUpRight className="h-3 w-3 opacity-0 transition-opacity duration-2 ease group-hover:opacity-100" />
        </Link>
        <span
          className={cn(
            "inline-flex items-center gap-1.5 rounded-[2px] px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide",
            is_stale
              ? "bg-warning/15 text-warning"
              : "bg-success/15 text-success",
          )}
          title={
            is_stale
              ? "Last ingest is older than the freshness threshold for this frequency."
              : "Within the freshness threshold for this frequency."
          }
        >
          <span
            aria-hidden
            className={cn(
              "h-1.5 w-1.5 rounded-full",
              is_stale ? "bg-warning" : "bg-success",
            )}
          />
          {is_stale ? "Stale" : "Fresh"}
        </span>
      </header>

      <dl className="grid grid-cols-2 gap-x-5 gap-y-3 p-5 text-xs">
        <div>
          <dt className="text-ink-3">Frequency</dt>
          <dd className="mt-1 text-ink">{formatFrequency(frequency)}</dd>
        </div>
        <div>
          <dt className="text-ink-3">Latest snapshot</dt>
          <dd className="mt-1 text-ink num">
            {formatDate(latest_snapshot_date)}
          </dd>
        </div>
        <div className="col-span-2">
          <dt className="text-ink-3">Last ingested</dt>
          <dd
            className="mt-1 text-ink num"
            title={formatDateTime(last_ingested_at)}
          >
            {last_ingested_at ? (
              <>
                {formatRelativeTime(last_ingested_at)}{" "}
                <span className="text-ink-3">
                  · {formatDateTime(last_ingested_at)}
                </span>
              </>
            ) : (
              "Never"
            )}
          </dd>
        </div>
      </dl>
    </article>
  );
}

function LoadingHealthGrid() {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: 3 }).map((_, i) => (
        <div
          key={i}
          className="h-40 animate-pulse rounded-lg border border-rule bg-surface"
        />
      ))}
    </div>
  );
}
