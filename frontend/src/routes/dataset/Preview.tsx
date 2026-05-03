import { useMemo, useState } from "react";
import { ChevronLeft, ChevronRight, Download } from "lucide-react";
import { useDatasetContext } from "./context";
import { DataTable } from "@/components/DataTable";
import { ErrorState } from "@/components/States";
import { useDatasetHistorical, useDatasetLatest } from "@/lib/queries";
import { formatDate } from "@/lib/format";
import { cn } from "@/lib/utils";

const PAGE_SIZE = 25;

export default function Preview() {
  const { slug, dataset } = useDatasetContext();

  const supportsCurrency = useMemo(
    () => dataset.fields.some((f) => f.name === "currency_code"),
    [dataset.fields],
  );

  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [currency, setCurrency] = useState("");
  const [offset, setOffset] = useState(0);

  const latest = useDatasetLatest(slug);
  const historical = useDatasetHistorical(slug, {
    from: from || undefined,
    to: to || undefined,
    currency: currency || undefined,
    limit: PAGE_SIZE,
    offset,
  });

  const total = historical.data?.meta.total ?? 0;
  const showingTo = Math.min(offset + PAGE_SIZE, total);

  function resetAndApply() {
    setOffset(0);
  }

  function clearFilters() {
    setFrom("");
    setTo("");
    setCurrency("");
    setOffset(0);
  }

  const csvHref = buildCsvHref(slug, { from, to, currency });

  return (
    <div className="space-y-12">
      {/* Latest snapshot */}
      <section>
        <header className="mb-4 flex items-baseline justify-between gap-3">
          <h2 className="font-display text-lg font-normal leading-tight tracking-tight">
            Latest snapshot
          </h2>
          <p className="text-xs text-ink-3">
            Snapshot date{" "}
            <span className="text-ink-2 num">
              {formatDate(latest.data?.meta.snapshot_date)}
            </span>{" "}
            ·{" "}
            <span className="text-ink-2 num">{latest.data?.meta.count ?? 0}</span>{" "}
            rows
          </p>
        </header>

        {latest.isLoading && (
          <div className="h-44 animate-pulse rounded-lg border border-rule bg-surface" />
        )}
        {latest.isError && (
          <ErrorState error={latest.error} context={`/datasets/${slug}/latest`} />
        )}
        {latest.data && <DataTable rows={latest.data.data} />}
      </section>

      {/* Historical */}
      <section>
        <header className="mb-4 flex flex-wrap items-baseline justify-between gap-3">
          <h2 className="font-display text-lg font-normal leading-tight tracking-tight">
            Historical
          </h2>
          <a
            href={csvHref}
            className="inline-flex items-center gap-1.5 rounded border border-rule px-3 py-1.5 text-xs transition-colors duration-2 ease hover:border-rule-2 hover:bg-accent-tint"
          >
            <Download className="h-3 w-3" />
            Export CSV {(from || to || currency) && "(filtered)"}
          </a>
        </header>

        <div className="mb-5 grid grid-cols-1 gap-3 rounded-lg border border-rule bg-surface-2 p-4 sm:grid-cols-[1fr_1fr_1fr_auto]">
          <Field label="From">
            <input
              type="date"
              value={from}
              onChange={(e) => {
                setFrom(e.target.value);
                resetAndApply();
              }}
              className="w-full rounded border border-rule bg-surface px-2.5 py-1.5 text-sm outline-none focus:border-accent focus:ring-2 focus:ring-accent/20"
            />
          </Field>
          <Field label="To">
            <input
              type="date"
              value={to}
              onChange={(e) => {
                setTo(e.target.value);
                resetAndApply();
              }}
              className="w-full rounded border border-rule bg-surface px-2.5 py-1.5 text-sm outline-none focus:border-accent focus:ring-2 focus:ring-accent/20"
            />
          </Field>
          {supportsCurrency ? (
            <Field label="Currency code">
              <input
                type="text"
                placeholder="USD"
                value={currency}
                maxLength={3}
                onChange={(e) => {
                  setCurrency(e.target.value.toUpperCase());
                  resetAndApply();
                }}
                className="w-full rounded border border-rule bg-surface px-2.5 py-1.5 font-mono text-sm uppercase outline-none focus:border-accent focus:ring-2 focus:ring-accent/20"
              />
            </Field>
          ) : (
            <div />
          )}
          <div className="flex items-end">
            {(from || to || currency) && (
              <button
                type="button"
                onClick={clearFilters}
                className="rounded border border-rule px-3 py-1.5 text-xs hover:border-rule-2 hover:bg-canvas"
              >
                Clear
              </button>
            )}
          </div>
        </div>

        <p className="mb-3 text-xs text-ink-3">
          {historical.isFetching && !historical.data && "Loading…"}
          {historical.data && (
            <>
              Showing{" "}
              <span className="text-ink-2 num">
                {total === 0 ? 0 : offset + 1}
              </span>
              {"–"}
              <span className="text-ink-2 num">{showingTo}</span> of{" "}
              <span className="text-ink-2 num">{total}</span> rows
            </>
          )}
        </p>

        {historical.isError && (
          <ErrorState
            error={historical.error}
            context={`/datasets/${slug}/historical`}
          />
        )}
        {historical.data && <DataTable rows={historical.data.data} />}

        {historical.data && total > PAGE_SIZE && (
          <div className="mt-4 flex items-center justify-end gap-2">
            <PageButton
              disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
              aria-label="Previous page"
            >
              <ChevronLeft className="h-3.5 w-3.5" />
              Prev
            </PageButton>
            <PageButton
              disabled={offset + PAGE_SIZE >= total}
              onClick={() => setOffset(offset + PAGE_SIZE)}
              aria-label="Next page"
            >
              Next
              <ChevronRight className="h-3.5 w-3.5" />
            </PageButton>
          </div>
        )}
      </section>
    </div>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-[10px] font-semibold uppercase tracking-[0.12em] text-ink-3">
        {label}
      </span>
      {children}
    </label>
  );
}

function PageButton({
  className,
  ...rest
}: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type="button"
      {...rest}
      className={cn(
        "inline-flex items-center gap-1 rounded border border-rule px-3 py-1.5 text-xs transition-colors duration-2 ease hover:border-rule-2 hover:bg-accent-tint disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:bg-transparent",
        className,
      )}
    />
  );
}

function buildCsvHref(
  slug: string,
  filters: { from?: string; to?: string; currency?: string },
): string {
  const params = new URLSearchParams();
  if (filters.from) params.set("from", filters.from);
  if (filters.to) params.set("to", filters.to);
  if (filters.currency) params.set("currency", filters.currency);
  const qs = params.toString();
  return `/api/datasets/${slug}/csv${qs ? `?${qs}` : ""}`;
}
