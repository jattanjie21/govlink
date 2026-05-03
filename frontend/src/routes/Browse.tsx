import { useMemo, useState } from "react";
import { Search, X } from "lucide-react";
import { Container } from "@/components/Container";
import { Breadcrumbs } from "@/components/Breadcrumbs";
import { DatasetCard } from "@/components/DatasetCard";
import { EmptyState, ErrorState, LoadingCardGrid } from "@/components/States";
import { useDatasets } from "@/lib/queries";
import type { DatasetSummary } from "@/lib/types";

type SortKey = "title" | "publisher" | "frequency";

const SORTS: ReadonlyArray<{ value: SortKey; label: string }> = [
  { value: "title", label: "Title (A→Z)" },
  { value: "publisher", label: "Publisher (A→Z)" },
  { value: "frequency", label: "Frequency" },
];

export default function Browse() {
  const { data, isLoading, isError, error } = useDatasets();
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<SortKey>("title");

  const filtered = useMemo(() => {
    if (!data) return [];
    const q = query.trim().toLowerCase();
    const matched = q
      ? data.filter((d) => matches(d, q))
      : [...data];
    return matched.sort(byKey(sort));
  }, [data, query, sort]);

  const totalCount = data?.length ?? 0;
  const matchCount = filtered.length;

  return (
    <>
      <section className="border-b border-rule pb-10 pt-12 md:pt-16">
        <Container>
          <Breadcrumbs items={[{ label: "Home", to: "/" }, { label: "Datasets" }]} />
          <h1 className="mt-6 font-display text-xl font-normal leading-tight tracking-tight">
            Datasets
          </h1>
          <p className="mt-3 max-w-prose text-sm text-ink-2">
            Every registered dataset, served from the same generic API
            endpoints. As the backend grows new dataset plugins, they
            appear here automatically.
          </p>
        </Container>
      </section>

      {/* Search + sort */}
      <section className="border-b border-rule bg-surface-2 py-4">
        <Container>
          <div className="flex w-full flex-col gap-3 sm:flex-row sm:items-center">
            <label className="relative flex-1">
              <Search
                aria-hidden
                className="pointer-events-none absolute left-3.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-ink-3"
              />
              <input
                type="search"
                placeholder="Search by title, publisher, or keyword (e.g. exchange, CBG, daily)…"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="w-full rounded border border-rule bg-surface px-9 py-2 text-sm text-ink outline-none transition-colors duration-2 ease placeholder:text-ink-3 focus:border-accent focus:ring-2 focus:ring-accent/20"
              />
              {query && (
                <button
                  type="button"
                  onClick={() => setQuery("")}
                  aria-label="Clear search"
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded p-1 text-ink-3 hover:bg-rule hover:text-ink"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              )}
            </label>

            <label className="flex items-center gap-2 text-xs text-ink-3">
              Sort
              <select
                value={sort}
                onChange={(e) => setSort(e.target.value as SortKey)}
                className="rounded border border-rule bg-surface px-2.5 py-2 text-sm text-ink outline-none focus:border-accent focus:ring-2 focus:ring-accent/20"
              >
                {SORTS.map((s) => (
                  <option key={s.value} value={s.value}>
                    {s.label}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </Container>
      </section>

      {/* Results */}
      <section className="py-10">
        <Container>
          <header className="mb-6 flex flex-wrap items-baseline justify-between gap-3 text-sm text-ink-3">
            <p>
              <span className="num text-ink">{matchCount}</span>{" "}
              {matchCount === 1 ? "dataset" : "datasets"}
              {query && (
                <>
                  {" "}
                  matching{" "}
                  <span className="text-ink">"{query}"</span>
                  {totalCount !== matchCount && (
                    <span className="text-ink-3"> · {totalCount} total</span>
                  )}
                </>
              )}
            </p>
          </header>

          {isLoading && <LoadingCardGrid count={3} />}
          {isError && <ErrorState error={error} context="GET /datasets" />}
          {!isLoading && !isError && filtered.length === 0 && (
            <EmptyState
              title={query ? "No matches" : "No datasets registered yet"}
              description={
                query
                  ? `Nothing matches "${query}". Try a broader term, or clear the search.`
                  : "Once a dataset plugin is registered in the backend, it will appear here."
              }
              action={
                query ? (
                  <button
                    type="button"
                    onClick={() => setQuery("")}
                    className="rounded border border-rule px-4 py-2 text-sm hover:bg-accent-tint hover:border-rule-2"
                  >
                    Clear search
                  </button>
                ) : undefined
              }
            />
          )}
          {filtered.length > 0 && (
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
              {filtered.map((d) => (
                <DatasetCard key={d.slug} dataset={d} />
              ))}
            </div>
          )}
        </Container>
      </section>
    </>
  );
}

function matches(d: DatasetSummary, q: string): boolean {
  return (
    d.title.toLowerCase().includes(q) ||
    d.publisher.toLowerCase().includes(q) ||
    d.description.toLowerCase().includes(q) ||
    d.slug.toLowerCase().includes(q)
  );
}

function byKey(key: SortKey) {
  return (a: DatasetSummary, b: DatasetSummary) => {
    const av = (a[key] ?? "").toLowerCase();
    const bv = (b[key] ?? "").toLowerCase();
    return av.localeCompare(bv);
  };
}
