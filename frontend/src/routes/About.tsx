import { Link } from "react-router-dom";
import { ArrowRight, ExternalLink } from "lucide-react";
import { Container } from "@/components/Container";
import { Eyebrow } from "@/components/Eyebrow";
import { Breadcrumbs } from "@/components/Breadcrumbs";
import { API_PUBLIC_URL } from "@/lib/env";

export default function About() {
  return (
    <>
      <section className="border-b border-rule py-20 md:py-24">
        <Container>
          <Breadcrumbs items={[{ label: "Home", to: "/" }, { label: "About" }]} />
          <Eyebrow className="mt-6">National data platform · The Gambia</Eyebrow>
          <h1 className="mt-6 max-w-[18ch] font-display text-[clamp(40px,5vw,64px)] font-normal leading-[1.05] tracking-tight">
            Open data,{" "}
            <em className="font-display italic text-accent">plainly served.</em>
          </h1>

          <div className="mt-8 grid gap-12 md:grid-cols-[1.4fr_1fr] md:items-start md:gap-16">
            <div className="max-w-[62ch] space-y-4 text-md leading-relaxed text-ink-2">
              <p>
                GovLink scrapes, parses, and normalises Gambian government
                data once, in the open, and serves it through a stable REST
                API. Starting with the Central Bank of The Gambia daily
                exchange rates and growing one dataset at a time. No sign-up.
                No quota gates. Citable, queryable, and structured.
              </p>
              <p>
                Public data published by Gambian institutions is overwhelmingly
                distributed as PDFs scattered across departmental websites —
                useful for a human reader, but effectively closed to anyone
                trying to build on it.
              </p>
            </div>

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

      <section className="border-b border-rule py-16">
        <Container>
          <div className="grid gap-10 md:grid-cols-3">
            <Audience
              label="Researchers"
              body="Cite a stable URL instead of a PDF that might move next quarter. Every snapshot is dated and historical queries are paginated."
            />
            <Audience
              label="Journalists"
              body="Pull the numbers behind a story without scraping a PDF table by hand. Export CSV in one click for spreadsheets and visualisations."
            />
            <Audience
              label="Developers"
              body="One generic API across every dataset. Decimals as JSON strings to preserve precision. Same shape, every endpoint."
            />
          </div>
        </Container>
      </section>

      <section className="border-b border-rule py-16">
        <Container>
          <div className="grid gap-10 md:grid-cols-[1fr_1.4fr]">
            <div>
              <Eyebrow>How it works</Eyebrow>
              <h2 className="mt-4 font-display text-xl font-normal leading-tight tracking-tight">
                Scraped once, served many ways.
              </h2>
            </div>
            <ol className="space-y-6 text-sm leading-relaxed text-ink-2">
              <Step n="01" title="Source">
                A Python ingestion plugin fetches the canonical artefact from
                the publishing institution — usually a PDF or HTML table on
                a government website.
              </Step>
              <Step n="02" title="Parse">
                The plugin extracts rows into a typed schema, validates
                values, and stores a dated snapshot in the database.
              </Step>
              <Step n="03" title="Serve">
                The same generic REST API exposes every registered dataset:
                metadata, latest snapshot, paginated history, CSV export.
              </Step>
              <Step n="04" title="Monitor">
                The{" "}
                <Link
                  to="/operator"
                  className="text-accent hover:text-accent-hover"
                >
                  operator page
                </Link>{" "}
                surfaces freshness for every dataset so stale data is
                visible to anyone, not just maintainers.
              </Step>
            </ol>
          </div>
        </Container>
      </section>

      <section className="border-b border-rule py-16">
        <Container>
          <div className="grid gap-10 md:grid-cols-[1fr_1.4fr]">
            <div>
              <Eyebrow>Sources</Eyebrow>
              <h2 className="mt-4 font-display text-xl font-normal leading-tight tracking-tight">
                Where the data comes from.
              </h2>
              <p className="mt-4 text-sm leading-relaxed text-ink-3">
                Every dataset detail page links back to the original
                publisher and artefact. We mirror, we don't replace.
              </p>
            </div>
            <dl className="space-y-5 text-sm">
              <Source
                publisher="Central Bank of The Gambia"
                dataset="Daily exchange rates"
                href="https://www.cbg.gm/"
              />
              <Source
                publisher="More publishers"
                dataset="Coming soon — each lands via the backend's plugin pattern"
              />
            </dl>
          </div>
        </Container>
      </section>

      <section className="border-b border-rule py-16">
        <Container>
          <div className="grid gap-10 md:grid-cols-[1fr_1.4fr]">
            <div>
              <Eyebrow>Open by default</Eyebrow>
              <h2 className="mt-4 font-display text-xl font-normal leading-tight tracking-tight">
                Code is MIT. Data follows the source.
              </h2>
            </div>
            <div className="space-y-4 text-sm leading-relaxed text-ink-2">
              <p>
                The GovLink codebase — frontend and backend — is released
                under the MIT License. The data itself is republished as
                published by the source institution; consult the publisher
                for the licence that applies to the underlying dataset.
              </p>
              <p>
                Contributions of any size are welcome — bug reports, new
                dataset plugins, UI improvements, documentation fixes. The
                goal is for any Gambian (and anyone else who cares) to be
                able to contribute.
              </p>
              <div className="flex flex-wrap gap-3 pt-2">
                <a
                  href="https://github.com/jattanjie21/govlink"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 rounded bg-accent px-4 py-2 text-sm font-medium text-white transition-colors duration-2 ease hover:bg-accent-hover"
                >
                  GitHub repository
                  <ExternalLink className="h-3.5 w-3.5" />
                </a>
                <Link
                  to="/api-docs"
                  className="inline-flex items-center gap-1.5 rounded border border-rule px-4 py-2 text-sm transition-colors duration-2 ease hover:border-rule-2 hover:bg-accent-tint"
                >
                  API documentation
                  <ArrowRight className="h-3.5 w-3.5" />
                </Link>
              </div>
            </div>
          </div>
        </Container>
      </section>

      {/* Developer strip */}
      <section className="border-b border-rule py-16">
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

      <section className="py-16">
        <Container>
          <div className="rounded-lg border border-rule bg-surface p-8 md:p-10">
            <Eyebrow>Get in touch</Eyebrow>
            <h2 className="mt-4 font-display text-lg font-normal leading-tight tracking-tight">
              Found a bug, want a dataset, or want to contribute?
            </h2>
            <p className="mt-3 max-w-[60ch] text-sm leading-relaxed text-ink-2">
              File an issue on GitHub — that's the fastest route. Pull
              requests for new dataset plugins, parser fixes, or UI
              improvements are very welcome.
            </p>
            <div className="mt-6">
              <a
                href="https://github.com/jattanjie21/govlink/issues"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-sm font-medium text-accent hover:text-accent-hover"
              >
                Open an issue on GitHub
                <ExternalLink className="h-3.5 w-3.5" />
              </a>
            </div>
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

function Audience({ label, body }: { label: string; body: string }) {
  return (
    <div>
      <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-accent">
        {label}
      </p>
      <p className="mt-3 text-sm leading-relaxed text-ink-2">{body}</p>
    </div>
  );
}

function Step({
  n,
  title,
  children,
}: {
  n: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <li className="grid grid-cols-[auto_1fr] gap-5">
      <span className="num text-[10px] font-semibold uppercase tracking-[0.12em] text-ink-3">
        {n}
      </span>
      <div>
        <p className="font-medium text-ink">{title}</p>
        <p className="mt-1 text-ink-2">{children}</p>
      </div>
    </li>
  );
}

function Source({
  publisher,
  dataset,
  href,
}: {
  publisher: string;
  dataset: string;
  href?: string;
}) {
  return (
    <div className="grid grid-cols-[1fr_auto] items-baseline gap-4 border-b border-rule pb-4 last:border-b-0 last:pb-0">
      <div>
        <dt className="font-medium text-ink">{publisher}</dt>
        <dd className="mt-1 text-ink-3">{dataset}</dd>
      </div>
      {href && (
        <a
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex shrink-0 items-center gap-1 text-xs text-accent hover:text-accent-hover"
        >
          Source
          <ExternalLink className="h-3 w-3" />
        </a>
      )}
    </div>
  );
}
