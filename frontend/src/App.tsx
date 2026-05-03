import { Routes, Route } from "react-router-dom";
import { useTheme } from "@/lib/theme";

export default function App() {
  const { theme, toggle } = useTheme();

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
                Stack: TypeScript, Tailwind v3 (with the design-system
                tokens), Router v7, TanStack Query v5. Theme toggle persists
                to <code className="font-mono text-sm">localStorage["govlink-theme"]</code>.
                Pages land in subsequent steps.
              </p>

              <button
                type="button"
                onClick={toggle}
                className="mt-8 inline-flex items-center gap-2 rounded border border-rule px-4 py-2 text-sm hover:border-rule-2 hover:bg-accent-tint transition-colors duration-2 ease"
              >
                Toggle theme · current: <span className="font-mono">{theme}</span>
              </button>
            </div>
          </main>
        }
      />
    </Routes>
  );
}
