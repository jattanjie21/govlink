import { NavLink, Link } from "react-router-dom";
import { Container } from "./Container";
import { ThemeToggle } from "./ThemeToggle";
import { cn } from "@/lib/utils";

interface NavItem {
  to: string;
  label: string;
  end?: boolean;
}

const NAV: NavItem[] = [
  { to: "/datasets", label: "Datasets" },
  { to: "/operator", label: "Operator" },
  { to: "/api-docs", label: "Developers" },
];

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-50 border-b border-rule bg-canvas/85 backdrop-blur-sm supports-[backdrop-filter]:bg-canvas/70">
      <Container>
        <div className="flex h-16 items-center gap-8">
          <Link
            to="/"
            className="flex items-baseline gap-2 font-display text-lg font-semibold tracking-tight"
          >
            <span
              aria-hidden
              className="inline-block h-6 w-2 translate-y-1 bg-accent"
            />
            GovLink
          </Link>

          <nav
            aria-label="Primary"
            className="-mx-2 flex items-center gap-3 overflow-x-auto px-2 sm:mx-0 sm:gap-6 sm:overflow-visible sm:px-0"
          >
            {NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  cn(
                    "shrink-0 text-xs transition-colors duration-2 ease sm:text-sm",
                    isActive ? "text-ink" : "text-ink-3 hover:text-ink",
                  )
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>

          <div className="ml-auto flex items-center gap-3">
            <ThemeToggle />
          </div>
        </div>
      </Container>
    </header>
  );
}
