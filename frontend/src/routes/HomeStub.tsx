import { Link } from "react-router-dom";
import { Container } from "@/components/Container";
import { useDatasets } from "@/lib/queries";
import { ApiError } from "@/lib/api";
import { formatFrequency } from "@/lib/format";

export default function HomeStub() {
  const { data, isLoading, isError, error } = useDatasets();

  return (
    <Container>
      <section className="py-24">
        <p className="text-eyebrow uppercase text-ink-3">
          National data platform · The Gambia
        </p>
        <h1 className="mt-6 max-w-[18ch] font-display text-display tracking-tight">
          Layout chrome ready.
        </h1>
        <p className="mt-6 max-w-prose text-md text-ink-2">
          Sticky header, sticky footer, and the design tokens are live.
          Pages land in step 4 onward. Below: a temporary smoke list to
          confirm the wired backend.
        </p>

        <div className="mt-10 flex gap-3">
          <Link
            to="/datasets"
            className="rounded bg-accent px-4 py-2 text-sm font-medium text-white transition-colors duration-2 ease hover:bg-accent-hover"
          >
            Browse datasets
          </Link>
          <Link
            to="/operator"
            className="rounded border border-rule px-4 py-2 text-sm transition-colors duration-2 ease hover:bg-accent-tint hover:border-rule-2"
          >
            Operator health
          </Link>
        </div>

        <div className="mt-12 border-t border-rule pt-8">
          <h2 className="font-display text-lg">Datasets (live)</h2>
          {isLoading && <p className="mt-3 text-sm text-ink-3">Loading…</p>}
          {isError && (
            <p className="mt-3 text-sm text-danger">
              {error instanceof ApiError
                ? `${error.code}: ${error.message}`
                : String(error)}
            </p>
          )}
          {data && (
            <ul className="mt-4 space-y-2">
              {data.map((d) => (
                <li
                  key={d.slug}
                  className="rounded border border-rule p-4 text-sm"
                >
                  <p className="font-medium text-ink">{d.title}</p>
                  <p className="mt-1 text-xs text-ink-3">
                    {d.publisher} · {formatFrequency(d.frequency)} ·{" "}
                    <span className="font-mono">{d.slug}</span>
                  </p>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>
    </Container>
  );
}
