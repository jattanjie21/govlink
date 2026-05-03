import { Routes, Route } from "react-router-dom";
import { useTheme } from "@/lib/theme";
import { useDatasets } from "@/lib/queries";
import { ApiError } from "@/lib/api";
import { formatFrequency } from "@/lib/format";

export default function App() {
  const { theme, toggle } = useTheme();
  const datasets = useDatasets();

  return (
    <Routes>
      <Route
        path="/"
        element={
          <main className="min-h-screen px-8 py-24">
            <div className="mx-auto max-w-content">
              <p className="text-eyebrow uppercase text-ink-3">GovLink</p>
              <h1 className="font-display text-display tracking-tight mt-4">
                Foundation ready.
              </h1>
              <p className="mt-6 text-md text-ink-2 max-w-prose">
                Step 2 — shared utilities live. The list below proves the
                axios client + envelope unwrap + queries module are wired
                against the FastAPI backend at{" "}
                <code className="font-mono text-sm">/api</code>.
              </p>

              <button
                type="button"
                onClick={toggle}
                className="mt-8 inline-flex items-center gap-2 rounded border border-rule px-4 py-2 text-sm hover:border-rule-2 hover:bg-accent-tint transition-colors duration-2 ease"
              >
                Toggle theme · current: <span className="font-mono">{theme}</span>
              </button>

              <section className="mt-12 border-t border-rule pt-8">
                <h2 className="font-display text-lg">Datasets (live)</h2>
                {datasets.isLoading && (
                  <p className="mt-3 text-sm text-ink-3">Loading…</p>
                )}
                {datasets.isError && (
                  <p className="mt-3 text-sm text-danger">
                    {datasets.error instanceof ApiError
                      ? `${datasets.error.code}: ${datasets.error.message}`
                      : String(datasets.error)}
                    <span className="ml-2 text-ink-3">
                      (start the backend on :8000 — see frontend/.env.example)
                    </span>
                  </p>
                )}
                {datasets.data && (
                  <ul className="mt-4 space-y-2">
                    {datasets.data.map((d) => (
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
              </section>
            </div>
          </main>
        }
      />
    </Routes>
  );
}
