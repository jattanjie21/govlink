import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { Container } from "@/components/Container";
import { Eyebrow } from "@/components/Eyebrow";

export default function NotFound() {
  return (
    <Container>
      <section className="mx-auto max-w-prose py-24 text-center sm:py-32">
        <Eyebrow className="justify-center">Error 404</Eyebrow>
        <h1 className="mt-6 font-display text-display font-normal leading-[1.05] tracking-tight">
          Nothing here.
        </h1>
        <p className="mt-5 text-md text-ink-2">
          The page you're looking for doesn't exist — it may have moved, or the
          link you followed was incorrect.
        </p>

        <div className="mt-10 flex flex-wrap justify-center gap-3">
          <Link
            to="/"
            className="inline-flex items-center gap-1.5 rounded bg-accent px-4 py-2 text-sm font-medium text-white transition-colors duration-2 ease hover:bg-accent-hover"
          >
            Home
          </Link>
          <Link
            to="/datasets"
            className="inline-flex items-center gap-1.5 rounded border border-rule px-4 py-2 text-sm transition-colors duration-2 ease hover:border-rule-2 hover:bg-accent-tint"
          >
            Browse datasets
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      </section>
    </Container>
  );
}
