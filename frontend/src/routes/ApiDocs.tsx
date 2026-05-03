import { Link } from "react-router-dom";
import { ArrowUpRight, ExternalLink } from "lucide-react";
import { Container } from "@/components/Container";
import { Eyebrow } from "@/components/Eyebrow";
import { Breadcrumbs } from "@/components/Breadcrumbs";
import { useDatasets } from "@/lib/queries";
import { ErrorState, LoadingCardGrid } from "@/components/States";
import { API_PUBLIC_URL } from "@/lib/env";

interface EndpointRow {
  method: "GET";
  path: string;
  description: string;
  rateLimited: boolean;
}

const ENDPOINTS: ReadonlyArray<EndpointRow> = [
  { method: "GET", path: "/", description: "Service info — name, version, docs URL.", rateLimited: false },
  { method: "GET", path: "/health", description: "Liveness probe.", rateLimited: false },
  { method: "GET", path: "/datasets", description: "List every registered dataset.", rateLimited: false },
  { method: "GET", path: "/datasets/{slug}", description: "Dataset metadata + field schema.", rateLimited: false },
  { method: "GET", path: "/datasets/{slug}/latest", description: "Most recent snapshot, all rows.", rateLimited: true },
  { method: "GET", path: "/datasets/{slug}/historical", description: "Paginated history with date / currency filters.", rateLimited: true },
  { method: "GET", path: "/datasets/{slug}/csv", description: "CSV stream of the same filters as historical.", rateLimited: true },
  { method: "GET", path: "/admin/health", description: "Per-dataset freshness — for monitoring.", rateLimited: false },
];

export default function ApiDocs() {
  const datasets = useDatasets();

  return (
    <>
      <section className="border-b border-rule pb-10 pt-12 md:pt-16">
        <Container>
          <Breadcrumbs items={[{ label: "Home", to: "/" }, { label: "API" }]} />
          <Eyebrow className="mt-6">For developers</Eyebrow>
          <h1 className="mt-4 font-display text-xl font-normal leading-tight tracking-tight">
            One API, every dataset.
          </h1>
          <p className="mt-3 max-w-prose text-sm text-ink-2">
            Every registered dataset exposes the same generic endpoints. No
            sign-up, no API keys — just stable JSON. Decimals are JSON
            strings to preserve precision. Responses are wrapped in a{" "}
            <code className="font-mono text-xs">{`{ data, meta }`}</code>{" "}
            envelope; errors in{" "}
            <code className="font-mono text-xs">{`{ error: { code, message } }`}</code>.
          </p>

          <div className="mt-6 flex flex-wrap gap-3">
            <a
              href={`${API_PUBLIC_URL}/docs`}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 rounded bg-accent px-4 py-2 text-sm font-medium text-white transition-colors duration-2 ease hover:bg-accent-hover"
            >
              Swagger UI
              <ExternalLink className="h-3.5 w-3.5" />
            </a>
            <a
              href={`${API_PUBLIC_URL}/openapi.json`}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 rounded border border-rule px-4 py-2 text-sm transition-colors duration-2 ease hover:border-rule-2 hover:bg-accent-tint"
            >
              OpenAPI JSON
              <ExternalLink className="h-3.5 w-3.5" />
            </a>
          </div>
        </Container>
      </section>

      <section className="border-b border-rule py-12">
        <Container>
          <h2 className="mb-6 font-display text-lg font-normal leading-tight tracking-tight">
            Endpoints
          </h2>
          <div className="overflow-x-auto rounded-lg border border-rule bg-surface">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-rule text-[10px] font-semibold uppercase tracking-[0.12em] text-ink-3">
                  <th className="px-4 py-3 text-left">Method</th>
                  <th className="px-4 py-3 text-left">Path</th>
                  <th className="px-4 py-3 text-left">Purpose</th>
                  <th className="px-4 py-3 text-right">Rate limit</th>
                </tr>
              </thead>
              <tbody>
                {ENDPOINTS.map((e) => (
                  <tr
                    key={e.path}
                    className="border-b border-rule last:border-b-0"
                  >
                    <td className="px-4 py-3">
                      <span className="rounded bg-accent-tint px-1.5 py-0.5 font-mono text-[10px] font-semibold text-accent">
                        {e.method}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-ink">
                      {e.path}
                    </td>
                    <td className="px-4 py-3 text-ink-2">{e.description}</td>
                    <td className="px-4 py-3 text-right text-xs text-ink-3">
                      {e.rateLimited ? (
                        <span className="num">60 / min / IP</span>
                      ) : (
                        "—"
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-3 text-xs text-ink-3">
            Live "Try it" interface for any endpoint sits inside each
            dataset's <span className="text-ink-2">API</span> tab.
          </p>
        </Container>
      </section>

      <section className="py-12">
        <Container>
          <h2 className="mb-6 font-display text-lg font-normal leading-tight tracking-tight">
            Try it on a dataset
          </h2>

          {datasets.isLoading && <LoadingCardGrid count={3} />}
          {datasets.isError && (
            <ErrorState error={datasets.error} context="GET /datasets" />
          )}
          {datasets.data && (
            <ul className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
              {datasets.data.map((d) => (
                <li key={d.slug}>
                  <Link
                    to={`/datasets/${d.slug}/api`}
                    className="group flex items-center justify-between rounded-lg border border-rule bg-surface px-5 py-4 text-sm transition-all duration-2 ease hover:-translate-y-px hover:border-ink-3"
                  >
                    <div>
                      <p className="font-medium text-ink">{d.title}</p>
                      <p className="mt-1 font-mono text-xs text-ink-3">
                        {d.slug}
                      </p>
                    </div>
                    <ArrowUpRight className="h-4 w-4 text-accent opacity-0 transition-opacity duration-2 ease group-hover:opacity-100" />
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Container>
      </section>
    </>
  );
}
