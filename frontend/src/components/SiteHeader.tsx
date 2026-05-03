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
  { to: "/api-docs", label: "API" },
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

          <nav aria-label="Primary" className="hidden gap-6 sm:flex">
            {NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  cn(
                    "text-sm transition-colors duration-2 ease",
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
