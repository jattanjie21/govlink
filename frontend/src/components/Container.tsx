import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

/**
 * The mock's `.wrap` — 1280px max, responsive horizontal padding.
 * Use on every section that needs the standard outer margin.
 */
export function Container({
  className,
  ...rest
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      {...rest}
      className={cn(
        "mx-auto w-full max-w-[1280px] px-5 sm:px-8",
        className,
      )}
    />
  );
}
