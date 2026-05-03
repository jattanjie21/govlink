import { ExternalLink } from "lucide-react";
import { useDatasetContext } from "./context";

export default function Overview() {
  const { dataset } = useDatasetContext();

  return (
    <div className="grid gap-12 lg:grid-cols-[1.6fr_1fr]">
      <article className="prose-content">
        <h2 className="font-display text-lg font-normal leading-tight tracking-tight">
          About this dataset
        </h2>
        <p className="mt-4 text-sm leading-relaxed text-ink-2">
          {dataset.description}
        </p>

        <h2 className="mt-12 font-display text-lg font-normal leading-tight tracking-tight">
          Schema
        </h2>
        <p className="mt-2 text-sm text-ink-3">
          {dataset.fields.length} field{dataset.fields.length === 1 ? "" : "s"} in
          table <code className="font-mono text-xs text-ink-2">{dataset.data_table_name}</code>.
        </p>

        <div className="mt-5 overflow-x-auto rounded-lg border border-rule bg-surface">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-rule text-[10px] font-semibold uppercase tracking-[0.12em] text-ink-3">
                <th className="px-4 py-3 text-left">Field</th>
                <th className="px-4 py-3 text-left">Type</th>
              </tr>
            </thead>
            <tbody>
              {dataset.fields.map((f) => (
                <tr
                  key={f.name}
                  className="border-b border-rule last:border-b-0"
                >
                  <td className="px-4 py-3 font-mono text-xs text-ink">
                    {f.name}
                  </td>
                  <td className="px-4 py-3 text-xs text-ink-2">
                    <span className="rounded-[2px] border border-rule bg-surface-2 px-1.5 py-0.5 font-mono">
                      {prettifyType(f.type)}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </article>

      <aside className="space-y-8">
        <div className="rounded-lg border border-rule bg-surface p-6">
          <h3 className="text-[10px] font-semibold uppercase tracking-[0.12em] text-ink-3">
            Source
          </h3>
          <p className="mt-2 text-sm text-ink-2">{dataset.publisher}</p>
          <a
            href={dataset.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-3 inline-flex items-center gap-1.5 text-xs font-medium text-accent hover:text-accent-hover"
          >
            Visit publisher
            <ExternalLink className="h-3 w-3" />
          </a>
        </div>

        <div className="rounded-lg border border-rule bg-surface p-6">
          <h3 className="text-[10px] font-semibold uppercase tracking-[0.12em] text-ink-3">
            Identifiers
          </h3>
          <dl className="mt-3 space-y-2.5 text-xs">
            <div>
              <dt className="text-ink-3">Slug</dt>
              <dd className="mt-0.5 font-mono text-ink">{dataset.slug}</dd>
            </div>
            <div>
              <dt className="text-ink-3">Storage table</dt>
              <dd className="mt-0.5 font-mono text-ink">
                {dataset.data_table_name}
              </dd>
            </div>
            <div>
              <dt className="text-ink-3">Update cadence</dt>
              <dd className="mt-0.5 capitalize text-ink">{dataset.frequency}</dd>
            </div>
          </dl>
        </div>
      </aside>
    </div>
  );
}

/**
 * The backend serializes Python type repr — e.g. "<class 'datetime.date'>".
 * Strip it down to a friendly token.
 */
function prettifyType(raw: string): string {
  const m = /'([^']+)'/.exec(raw);
  if (!m) return raw;
  const fq = m[1];
  // drop module prefix: "datetime.date" → "date"
  const last = fq.split(".").pop() ?? fq;
  return last;
}
