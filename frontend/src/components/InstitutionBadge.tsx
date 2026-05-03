import { useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { ShieldCheck } from "lucide-react";
import { INSTITUTIONS } from "@/lib/institutions";
import { slugify } from "@/lib/utils";
import { cn } from "@/lib/utils";

interface InstitutionBadgeProps {
  publisher: string;
  /** When true, render as a Link to /institutions/:slug. Off inside another <Link>. */
  linked?: boolean;
  size?: "sm" | "md";
  className?: string;
}

const SIZES = {
  sm: {
    wrap: "gap-2 px-2.5 py-1 text-xs",
    logo: "h-4 w-4",
    initial: "text-[10px]",
  },
  md: {
    wrap: "gap-2.5 px-3 py-1.5 text-sm",
    logo: "h-5 w-5",
    initial: "text-xs",
  },
} as const;

export function InstitutionBadge({
  publisher,
  linked = false,
  size = "sm",
  className,
}: InstitutionBadgeProps) {
  const [logoBroken, setLogoBroken] = useState(false);
  const slug = slugify(publisher);
  const meta = INSTITUTIONS[slug];
  const logoUrl = meta?.logoUrl;
  const verified = !!meta;
  const sizing = SIZES[size];
  const initial = (publisher[0] ?? "?").toUpperCase();

  const inner: ReactNode = (
    <>
      <span
        aria-hidden
        className={cn(
          "inline-flex shrink-0 items-center justify-center overflow-hidden rounded-[3px] transition-colors duration-2 ease",
          sizing.logo,
          logoUrl && !logoBroken ? "bg-white" : "bg-accent-tint",
        )}
      >
        {logoUrl && !logoBroken ? (
          <img
            src={logoUrl}
            alt=""
            className="h-full w-full object-contain p-0.5"
            onError={() => setLogoBroken(true)}
          />
        ) : (
          <span
            className={cn(
              "font-display font-semibold text-accent",
              sizing.initial,
            )}
          >
            {initial}
          </span>
        )}
      </span>
      <span className="text-ink-2">{publisher}</span>
      {verified && (
        <span
          className="inline-flex items-center gap-1 text-xs font-medium text-success"
          title="Publisher source verified"
        >
          <ShieldCheck className="h-3 w-3" /> Verified
        </span>
      )}
    </>
  );

  const baseClasses = cn(
    "inline-flex items-center rounded border border-rule bg-surface transition-all duration-2 ease",
    sizing.wrap,
    linked && "hover:-translate-y-px hover:border-rule-2 hover:bg-accent-tint",
    className,
  );

  if (linked) {
    return (
      <Link to={`/institutions/${slug}`} className={baseClasses}>
        {inner}
      </Link>
    );
  }
  return <span className={baseClasses}>{inner}</span>;
}
