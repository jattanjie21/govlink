import { NavLink, Outlet, useLocation, useParams } from "react-router-dom";
import { Download, ExternalLink } from "lucide-react";
import { Container } from "@/components/Container";
import { Breadcrumbs } from "@/components/Breadcrumbs";
import { InstitutionBadge } from "@/components/InstitutionBadge";
import { ErrorState } from "@/components/States";
import { useDataset, useHealth } from "@/lib/queries";
import { formatDate, formatDateTime, formatFrequency } from "@/lib/format";
import { cn } from "@/lib/utils";

export default function DatasetLayout() {
  const { slug = "" } = useParams<{ slug: string }>();
  const dataset = useDataset(slug);
  const health = useHealth(60_000);
  const location = useLocation();

  if (dataset.isLoading) {
    return (
      <Container>
        <div className="py-16 text-sm text-ink-3">Loading dataset…</div>
      </Container>
    );
  }

  if (dataset.isError || !dataset.data) {
    return (
      <Container>
        <div className="py-16">
          <ErrorState error={dataset.error} context={`GET /datasets/${slug}`} />
        </div>
      </Container>
    );
  }

  const d = dataset.data;
  const freshness = health.data?.datasets.find((x) => x.slug === slug);

  const csvHref = `/api/datasets/${slug}/csv`;

  return (
    <>
      {/* Hero */}
      <section className="animate-fade-up border-b border-rule pb-10 pt-12 md:pt-16">
        <Container>
          <Breadcrumbs
            items={[
              { label: "Home", to: "/" },
              { label: d.title },
            ]}
          />

          <div className="mt-6 flex flex-wrap items-center gap-3">
            <InstitutionBadge publisher={d.publisher} linked />
          </div>

          <h1 className="mt-5 max-w-[22ch] font-display text-[clamp(32px,4vw,52px)] font-normal leading-[1.05] tracking-tight">
            {d.title}
          </h1>
          <p className="mt-5 max-w-[68ch] text-md leading-relaxed text-ink-2">
            {d.description}
          </p>

          {/* Meta strip */}
          <dl className="mt-8 grid grid-cols-2 gap-x-8 gap-y-4 border-t border-rule pt-6 sm:grid-cols-4">
            <Meta label="Frequency">{formatFrequency(d.frequency)}</Meta>
            <Meta label="Latest snapshot">
              {formatDate(freshness?.latest_snapshot_date)}
            </Meta>
            <Meta label="Last ingested">
              {formatDateTime(freshness?.last_ingested_at)}
            </Meta>
            <Meta label="Status">
              {freshness ? (
                <span
                  className={cn(
                    "inline-flex items-center gap-1.5 rounded-[2px] px-1.5 py-0.5 text-xs",
                    freshness.is_stale
                      ? "bg-warning/15 text-warning"
                      : "bg-success/15 text-success",
                  )}
                >
                  <span
                    aria-hidden
                    className={cn(
                      "h-1.5 w-1.5 rounded-full",
                      freshness.is_stale ? "bg-warning" : "bg-success",
                    )}
                  />
                  {freshness.is_stale ? "Stale" : "Fresh"}
                </span>
              ) : (
                "—"
              )}
            </Meta>
          </dl>

          {/* CTA row */}
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <a
              href={csvHref}
              className="inline-flex items-center gap-2 rounded bg-accent px-4 py-2 text-sm font-medium text-white transition-colors duration-2 ease hover:bg-accent-hover"
            >
              <Download className="h-3.5 w-3.5" />
              Download CSV
            </a>
            <a
              href={d.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 rounded border border-rule px-4 py-2 text-sm transition-colors duration-2 ease hover:border-rule-2 hover:bg-accent-tint"
            >
              View source
              <ExternalLink className="h-3.5 w-3.5" />
            </a>
            <NavLink
              to={`/datasets/${slug}/api`}
              className="inline-flex items-center gap-2 rounded border border-rule px-3 py-1.5 font-mono text-xs text-ink-2 transition-colors duration-2 ease hover:bg-accent-tint hover:text-ink"
            >
              <span className="font-sans uppercase tracking-wider text-ink-3">API</span>
              <span className="rounded bg-accent-tint px-1.5 py-0.5 text-[10px] font-semibold text-accent">
                GET
              </span>
              <span>/datasets/{slug}/latest</span>
            </NavLink>
          </div>
        </Container>
      </section>

      {/* Tab bar */}
      <div className="sticky top-16 z-40 border-b border-rule bg-canvas/85 backdrop-blur-sm">
        <Container>
          <div role="tablist" className="flex gap-1 overflow-x-auto">
            <Tab to={`/datasets/${slug}`} end>
              Preview
            </Tab>
            <Tab to={`/datasets/${slug}/overview`}>Overview</Tab>
            <Tab to={`/datasets/${slug}/api`}>API</Tab>
          </div>
        </Container>
      </div>

      {/* Tab content */}
      <section className="py-10">
        <Container>
          <div
            key={location.pathname}
            className="animate-in fade-in-0 slide-in-from-bottom-1 duration-300"
          >
            <Outlet context={{ slug, dataset: d, freshness }} />
          </div>
        </Container>
      </section>
    </>
  );
}

function Tab({
  to,
  end,
  children,
}: {
  to: string;
  end?: boolean;
  children: React.ReactNode;
}) {
  return (
    <NavLink
      to={to}
      end={end}
      role="tab"
      className={({ isActive }) =>
        cn(
          "relative px-4 py-3.5 text-sm transition-colors duration-2 ease",
          isActive ? "text-ink" : "text-ink-3 hover:text-ink",
          isActive &&
            "after:absolute after:bottom-[-1px] after:left-3 after:right-3 after:h-[2px] after:bg-accent",
        )
      }
    >
      {children}
    </NavLink>
  );
}

function Meta({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="text-[10px] font-semibold uppercase tracking-[0.12em] text-ink-3">
        {label}
      </dt>
      <dd className="mt-1.5 text-sm text-ink num">{children}</dd>
    </div>
  );
}

