import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { Container } from "@/components/Container";
import { Eyebrow } from "@/components/Eyebrow";
import { DatasetCard } from "@/components/DatasetCard";
import { EmptyState, ErrorState, LoadingCardGrid } from "@/components/States";
import { useDatasets } from "@/lib/queries";
import { API_PUBLIC_URL } from "@/lib/env";

export default function Home() {
  const { data, isLoading, isError, error } = useDatasets();

  return (
    <>
      {/* Hero */}
      <section className="border-b border-rule py-20 md:py-24">
        <Container>
          <Eyebrow>National data platform · The Gambia</Eyebrow>
          <h1 className="mt-6 max-w-[18ch] font-display text-[clamp(40px,5vw,64px)] font-normal leading-[1.05] tracking-tight">
            Open data,{" "}
            <em className="font-display italic text-accent">plainly served.</em>
          </h1>

          <div className="mt-8 grid gap-12 md:grid-cols-[1.4fr_1fr] md:items-start md:gap-16">
            <p className="max-w-[62ch] text-md leading-relaxed text-ink-2">
              GovLink scrapes, parses, and normalises Gambian government data
              once, in the open, and serves it through a stable REST API.
              Starting with the Central Bank of The Gambia daily exchange
              rates and growing one dataset at a time. No sign-up. No quota
              gates. Citable, queryable, and structured.
            </p>

            <dl className="grid grid-cols-2 gap-x-6 gap-y-3.5 rounded-lg border border-rule bg-surface px-6 py-5 text-sm">
              <Meta label="Audience">Researchers · journalists · devs</Meta>
              <Meta label="Datasets">Growing</Meta>
              <Meta label="Rate limit">60 req/min</Meta>
              <Meta label="Auth">None</Meta>
              <Meta label="License">MIT (code) · Source as published</Meta>
            </dl>
          </div>
        </Container>
      </section>

      {/* Featured datasets */}
      <section className="border-b border-rule py-20">
        <Container>
          <header className="mb-9 flex items-baseline justify-between gap-8">
            <div>
              <Eyebrow className="mb-3.5 flex">Datasets</Eyebrow>
              <h2 className="font-display text-xl font-normal leading-tight tracking-tight">
                Available now
              </h2>
            </div>
            <p className="max-w-[36ch] text-right text-sm text-ink-3">
              Each dataset is structured, paginated, and exportable as CSV.
              More land via the backend's plugin pattern.
            </p>
          </header>

          {isLoading && <LoadingCardGrid count={3} />}
          {isError && <ErrorState error={error} context="GET /datasets" />}
          {data && data.length === 0 && (
            <EmptyState
              title="No datasets registered yet"
              description="Once a dataset plugin is registered in the backend, it will appear here."
            />
          )}
          {data && data.length > 0 && (
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
              {data.map((d) => (
                <DatasetCard key={d.slug} dataset={d} />
              ))}
            </div>
          )}

          {data && data.length > 0 && (
            <div className="mt-10">
              <Link
                to="/datasets"
                className="inline-flex items-center gap-1.5 text-sm font-medium text-accent hover:text-accent-hover"
              >
                Browse all datasets
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </div>
          )}
        </Container>
      </section>

      {/* Developer strip */}
      <section className="py-20">
        <Container>
          <div className="grid gap-10 md:grid-cols-[1.2fr_1fr] md:items-center">
            <div>
              <Eyebrow>For developers</Eyebrow>
              <h2 className="mt-4 font-display text-xl font-normal leading-tight tracking-tight">
                One API, every dataset.
              </h2>
              <p className="mt-4 max-w-prose text-sm leading-relaxed text-ink-2">
                Every registered dataset exposes the same generic endpoints:
                metadata, latest snapshot, paginated history, CSV export. No
                per-dataset client code, no API keys, just stable JSON.
              </p>
              <div className="mt-7 flex flex-wrap gap-3">
                <Link
                  to="/api-docs"
                  className="inline-flex items-center gap-1.5 rounded bg-accent px-4 py-2 text-sm font-medium text-white transition-colors duration-2 ease hover:bg-accent-hover"
                >
                  API documentation
                  <ArrowRight className="h-3.5 w-3.5" />
                </Link>
                <a
                  href={`${API_PUBLIC_URL}/docs`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 rounded border border-rule px-4 py-2 text-sm transition-colors duration-2 ease hover:border-rule-2 hover:bg-accent-tint"
                >
                  Swagger UI
                </a>
              </div>
            </div>

            <pre className="overflow-x-auto rounded-lg border border-rule bg-[var(--code-bg)] p-5 font-mono text-xs leading-relaxed text-[var(--code-fg)]">
{`# Latest exchange-rate snapshot
curl ${API_PUBLIC_URL}/datasets/exchange-rates/latest

# Filter by date and currency
curl '${API_PUBLIC_URL}/datasets/exchange-rates/historical \\
  ?from=2026-01-01&to=2026-04-30&currency=USD'`}
            </pre>
          </div>
        </Container>
      </section>
    </>
  );
}

function Meta({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="text-[10px] font-semibold uppercase tracking-[0.12em] text-ink-3">
        {label}
      </dt>
      <dd className="mt-1 text-ink num">{children}</dd>
    </div>
  );
}
