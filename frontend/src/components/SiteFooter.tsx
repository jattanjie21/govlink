import { Container } from "./Container";

/**
 * Per brand-spec: a single 24×8 stripe in red·navy·forest is the
 * *only* permitted nod to flag colors, in the footer.
 */
export function SiteFooter() {
  const year = new Date().getFullYear();
  return (
    <footer className="mt-auto border-t border-rule bg-surface-2 py-8 text-xs text-ink-3">
      <Container>
        <div className="flex flex-col items-start justify-between gap-2 sm:flex-row sm:items-center">
          <div className="flex items-center gap-3.5">
            <span
              aria-hidden
              className="inline-flex h-2 w-6 items-center overflow-hidden rounded-[1px] border border-rule"
            >
              <span className="h-full flex-1 bg-[#CE1126]" />
              <span className="h-full flex-1 bg-[#0C1C8C]" />
              <span className="h-full flex-1 bg-[#3A7728]" />
            </span>
            <span>
              GovLink · Banjul · Open data for The Gambia
            </span>
          </div>
          <div className="flex items-center gap-3 num">
            <a
              href="https://github.com/jattanjie21/govlink"
              target="_blank"
              rel="noreferrer"
              className="text-ink-3 transition-colors duration-2 ease hover:text-ink"
            >
              GitHub
            </a>
            <span aria-hidden>·</span>
            <span>{year}</span>
          </div>
        </div>
      </Container>
    </footer>
  );
}
