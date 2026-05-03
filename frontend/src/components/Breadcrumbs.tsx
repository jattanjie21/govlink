import { Link } from "react-router-dom";
import { ChevronRight } from "lucide-react";
import type { ReactNode } from "react";

export interface Crumb {
  label: ReactNode;
  to?: string;
}

export function Breadcrumbs({ items }: { items: Crumb[] }) {
  return (
    <nav aria-label="Breadcrumb">
      <ol className="flex flex-wrap items-center gap-1.5 text-xs text-ink-3">
        {items.map((c, i) => (
          <li key={i} className="flex items-center gap-1.5">
            {c.to ? (
              <Link
                to={c.to}
                className="transition-colors duration-2 ease hover:text-ink"
              >
                {c.label}
              </Link>
            ) : (
              <span className="text-ink-2">{c.label}</span>
            )}
            {i < items.length - 1 && (
              <ChevronRight aria-hidden className="h-3 w-3 text-ink-3" />
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
}
