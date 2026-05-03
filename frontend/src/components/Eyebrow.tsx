import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

/**
 * The "eyebrow" pattern from the mocks — uppercase, tracked-out, with
 * a 24px hairline accent rule before it. Use above section/page titles.
 */
export function Eyebrow({
  className,
  children,
  ...rest
}: HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      {...rest}
      className={cn(
        "inline-flex items-center gap-2.5 text-eyebrow font-medium uppercase text-ink-3",
        "before:inline-block before:h-px before:w-6 before:bg-accent before:content-['']",
        className,
      )}
    >
      {children}
    </span>
  );
}
