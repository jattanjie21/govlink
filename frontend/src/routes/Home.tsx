import { useMemo, useState } from "react";
import { Search, X } from "lucide-react";
import { Container } from "@/components/Container";
import { Eyebrow } from "@/components/Eyebrow";
import { DatasetCard } from "@/components/DatasetCard";
import { InstitutionCard } from "@/components/InstitutionCard";
import { EmptyState, ErrorState, LoadingCardGrid } from "@/components/States";
import { useDatasets } from "@/lib/queries";
import { slugify } from "@/lib/utils";
import { INSTITUTIONS } from "@/lib/institutions";
import type { DatasetSummary } from "@/lib/types";

interface Institution {
  publisher: string;
  slug: string;
  datasets: DatasetSummary[];
}

function groupByInstitution(list: DatasetSummary[]): Institution[] {
  const map = new Map<string, Institution>();
  for (const d of list) {
    const slug = slugify(d.publisher);
    let inst = map.get(slug);
    if (!inst) {
      inst = { publisher: d.publisher, slug, datasets: [] };
      map.set(slug, inst);
    }
    inst.datasets.push(d);
  }
  return [...map.values()].sort((a, b) =>
    a.publisher.localeCompare(b.publisher),
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

export default function Home() {
  const { data, isLoading, isError, error } = useDatasets();
  const [query, setQuery] = useState("");

  const institutions = useMemo(
    () => (data ? groupByInstitution(data) : []),
    [data],
  );

  const q = query.trim().toLowerCase();
  const isSearching = q.length > 0;
  const filteredDatasets = useMemo(() => {
    if (!data || !isSearching) return [];
    return data.filter((d) => matches(d, q));
  }, [data, q, isSearching]);

  return (
    <>
      <section className="border-b border-rule py-12 md:py-16">
        <Container>
          <label className="relative mx-auto block max-w-2xl">
            <Search
              aria-hidden
              className="pointer-events-none absolute left-3.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-ink-3"
            />
            <input
              type="search"
              placeholder="Search datasets by title, publisher, or keyword (e.g. exchange, CBG, daily)…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-full rounded border border-rule bg-surface px-9 py-2.5 text-sm text-ink outline-none transition-colors duration-2 ease placeholder:text-ink-3 focus:border-accent focus:ring-2 focus:ring-accent/20"
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
        </Container>
      </section>

      <section className="py-10">
        <Container>
          <header className="mb-6 text-sm text-ink-3">
            {data && isSearching && (
              <p>
                <span className="num text-ink">{filteredDatasets.length}</span>{" "}
                {filteredDatasets.length === 1 ? "dataset" : "datasets"} matching{" "}
                <span className="text-ink">"{query}"</span>
                {data.length !== filteredDatasets.length && (
                  <span> · {data.length} total</span>
                )}
              </p>
            )}
            {data && !isSearching && (
              <p>
                <span className="num text-ink">{institutions.length}</span>{" "}
                {institutions.length === 1 ? "institution" : "institutions"}
                {" · "}
                <span className="num text-ink">{data.length}</span>{" "}
                {data.length === 1 ? "dataset" : "datasets"}
              </p>
            )}
          </header>

          {isLoading && <LoadingCardGrid count={3} />}
          {isError && <ErrorState error={error} context="GET /datasets" />}

          {!isLoading && !isError && isSearching && (
            <>
              {filteredDatasets.length === 0 && (
                <EmptyState
                  title="No matches"
                  description={`Nothing matches "${query}". Try a broader term, or clear the search.`}
                  action={
                    <button
                      type="button"
                      onClick={() => setQuery("")}
                      className="rounded border border-rule px-4 py-2 text-sm hover:bg-accent-tint hover:border-rule-2"
                    >
                      Clear search
                    </button>
                  }
                />
              )}
              {filteredDatasets.length > 0 && (
                <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
                  {filteredDatasets.map((d, i) => (
                    <div
                      key={d.slug}
                      className="animate-fade-up"
                      style={{ animationDelay: `${i * 50}ms` }}
                    >
                      <DatasetCard dataset={d} />
                    </div>
                  ))}
                </div>
              )}
            </>
          )}

          {!isLoading && !isError && !isSearching && (
            <>
              {data && institutions.length === 0 && (
                <EmptyState
                  title="No datasets registered yet"
                  description="Once a dataset plugin is registered in the backend, it will appear here."
                />
              )}
              {institutions.length > 0 && (
                <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
                  {institutions.map((inst, i) => {
                    const meta = INSTITUTIONS[inst.slug] ?? {};
                    return (
                      <div
                        key={inst.slug}
                        className="animate-fade-up"
                        style={{ animationDelay: `${i * 60}ms` }}
                      >
                        <InstitutionCard
                          publisher={inst.publisher}
                          slug={inst.slug}
                          datasetCount={inst.datasets.length}
                          sector={meta.sector}
                          description={meta.description}
                          logoUrl={meta.logoUrl}
                        />
                      </div>
                    );
                  })}
                </div>
              )}
            </>
          )}
        </Container>
      </section>

      <section className="border-t border-rule py-16 md:py-20">
        <Container>
          <Eyebrow>Datasets</Eyebrow>
          <h2 className="mt-4 font-display text-[clamp(32px,4vw,48px)] font-normal leading-[1.05] tracking-tight">
            Browse data by{" "}
            <em className="font-display italic text-accent">institution</em>.
          </h2>
          <p className="mt-5 text-md leading-relaxed text-ink-2">
            Each card represents a Gambian institution publishing structured
            data through GovLink. Open one to see every dataset from that
            publisher — or search across all datasets directly.
          </p>
        </Container>
      </section>
    </>
  );
}
