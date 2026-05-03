import { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Database } from "lucide-react";

interface InstitutionCardProps {
  publisher: string;
  slug: string;
  datasetCount: number;
  /** Short description of the institution (mission, mandate, sector). */
  description?: string;
  /** Sector / type label, e.g. "Central bank". Shown under the name. */
  sector?: string;
  /** Optional logo URL. If absent or fails to load, falls back to initials. */
  logoUrl?: string;
}

export function InstitutionCard({
  publisher,
  slug,
  datasetCount,
  description,
  sector,
  logoUrl,
}: InstitutionCardProps) {
  const [logoBroken, setLogoBroken] = useState(false);
  const initials = computeInitials(publisher);

  const fallbackDescription = `Publishing ${datasetCount} ${
    datasetCount === 1 ? "dataset" : "datasets"
  } through GovLink.`;

  return (
    <Link
      to={`/institutions/${slug}`}
      className="group relative block w-full overflow-hidden rounded-2xl border border-rule bg-surface shadow-sm transition-all duration-2 ease hover:-translate-y-px hover:border-ink-3 hover:shadow-lg"
    >
      <div
        className="h-28 w-full bg-gradient-to-br from-accent/40 via-accent/15 to-surface-2"
        aria-hidden
      />

      <div className="absolute left-1/2 top-28 -translate-x-1/2 -translate-y-1/2">
        <div className="flex h-20 w-20 items-center justify-center overflow-hidden rounded-full border-4 border-surface bg-surface-2 ring-1 ring-rule">
          {logoUrl && !logoBroken ? (
            <img
              src={logoUrl}
              alt={`${publisher} logo`}
              className="h-full w-full object-cover"
              onError={() => setLogoBroken(true)}
            />
          ) : (
            <span className="font-display text-md font-semibold text-ink num">
              {initials}
            </span>
          )}
        </div>
      </div>

      <div className="px-6 pb-6 pt-12 text-center">
        <h3 className="font-display text-lg leading-tight tracking-tight text-ink">
          {publisher}
        </h3>
        {sector && (
          <p className="mt-1 text-eyebrow font-semibold uppercase text-ink-3">
            {sector}
          </p>
        )}

        <p className="mt-3 line-clamp-3 min-h-[3.75em] text-sm leading-relaxed text-ink-2">
          {description ?? fallbackDescription}
        </p>

        <div className="my-5 inline-flex items-center gap-1.5 rounded-full border border-rule bg-surface-2/60 px-3 py-1 text-xs text-ink-3">
          <Database className="h-3 w-3" aria-hidden />
          <span className="num text-ink">{datasetCount}</span>
          <span>{datasetCount === 1 ? "dataset" : "datasets"}</span>
        </div>

        <div className="inline-flex w-full items-center justify-center gap-1.5 rounded bg-accent px-4 py-2.5 text-sm font-medium text-white transition-colors duration-2 ease group-hover:bg-accent-hover">
          View datasets
          <ArrowRight className="h-3.5 w-3.5" />
        </div>
      </div>
    </Link>
  );
}

function computeInitials(publisher: string): string {
  const skip = new Set(["of", "the", "and", "for"]);
  const initials = publisher
    .split(/\s+/)
    .filter((w) => w && !skip.has(w.toLowerCase()))
    .map((w) => w[0]?.toUpperCase() ?? "")
    .join("")
    .slice(0, 3);
  return initials || publisher.slice(0, 2).toUpperCase();
}
