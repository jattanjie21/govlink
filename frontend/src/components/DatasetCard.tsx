import { Link } from "react-router-dom";
import { ArrowUpRight } from "lucide-react";
import type { DatasetSummary } from "@/lib/types";
import { formatFrequency } from "@/lib/format";

/**
 * Editorial dataset card — used on Home (featured) and Browse (results).
 * Follows the mock's screen-card pattern: border, hover lift, eyebrow +
 * title + description, with a footer bar showing meta + arrow.
 */
export function DatasetCard({ dataset }: { dataset: DatasetSummary }) {
  return (
    <Link
      to={`/datasets/${dataset.slug}`}
      className="group flex flex-col rounded-lg border border-rule bg-surface transition-all duration-2 ease hover:-translate-y-px hover:border-ink-3"
    >
      <div className="flex-1 p-7">
        <div className="flex items-center gap-3 text-eyebrow font-semibold uppercase text-ink-3">
          <span className="font-display text-md font-normal text-ink-2 normal-case num">
            {dataset.publisher.split(" ").slice(0, 2).join(" ")}
          </span>
          <span aria-hidden className="h-3 w-px bg-rule-2" />
          <span>{formatFrequency(dataset.frequency)}</span>
        </div>

        <h3 className="mt-4 font-display text-lg leading-tight tracking-tight">
          {dataset.title}
        </h3>

        <p className="mt-3 line-clamp-3 text-sm leading-relaxed text-ink-2">
          {dataset.description}
        </p>
      </div>

      <div className="flex items-center justify-between border-t border-rule bg-surface-2 px-7 py-3.5 text-xs text-ink-3">
        <span className="font-mono">{dataset.slug}</span>
        <span className="inline-flex items-center gap-1 font-medium text-accent transition-transform duration-2 ease group-hover:translate-x-0.5">
          View
          <ArrowUpRight className="h-3 w-3" />
        </span>
      </div>
    </Link>
  );
}
