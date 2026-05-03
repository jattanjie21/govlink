import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { Container } from "@/components/Container";
import { Breadcrumbs } from "@/components/Breadcrumbs";
import { DatasetCard } from "@/components/DatasetCard";
import { Eyebrow } from "@/components/Eyebrow";
import { EmptyState, ErrorState, LoadingCardGrid } from "@/components/States";
import { useDatasets } from "@/lib/queries";
import { slugify } from "@/lib/utils";
import { INSTITUTIONS } from "@/lib/institutions";

export default function Institution() {
  const { institutionSlug } = useParams<{ institutionSlug: string }>();
  const { data, isLoading, isError, error } = useDatasets();
  const [logoBroken, setLogoBroken] = useState(false);

  const datasets = data
    ? data.filter((d) => slugify(d.publisher) === institutionSlug)
    : [];
  const publisher = datasets[0]?.publisher ?? "";
  const notFound = !!data && datasets.length === 0;
  const meta = institutionSlug ? INSTITUTIONS[institutionSlug] : undefined;
  const logoUrl = meta?.logoUrl;

  return (
    <>
      <section className="border-b border-rule pb-10 pt-12 md:pt-16">
        <Container>
          <Breadcrumbs
            items={[
              { label: "Home", to: "/" },
              { label: publisher || "Institution" },
            ]}
          />
          <Eyebrow className="mt-6">Institution</Eyebrow>

          <div className="mt-4 flex animate-fade-up items-start gap-5">
            {logoUrl && !logoBroken && (
              <div className="flex h-16 w-16 shrink-0 items-center justify-center overflow-hidden rounded-full border border-rule bg-white p-2 ring-1 ring-rule">
                <img
                  src={logoUrl}
                  alt={`${publisher} logo`}
                  className="h-full w-full object-contain"
                  onError={() => setLogoBroken(true)}
                />
              </div>
            )}
            <div>
              <h1 className="font-display text-xl font-normal leading-tight tracking-tight">
                {publisher || "Unknown institution"}
              </h1>
              {data && !notFound && (
                <p className="mt-2 text-sm text-ink-3">
                  <span className="num text-ink">{datasets.length}</span>{" "}
                  {datasets.length === 1 ? "dataset" : "datasets"} from this
                  publisher.
                </p>
              )}
            </div>
          </div>
        </Container>
      </section>

      <section className="py-10">
        <Container>
          {isLoading && <LoadingCardGrid count={3} />}
          {isError && <ErrorState error={error} context="GET /datasets" />}
          {notFound && (
            <EmptyState
              title="No datasets for this institution"
              description="The publisher slug in the URL doesn't match any registered datasets."
              action={
                <Link
                  to="/"
                  className="inline-flex items-center gap-1.5 rounded border border-rule px-4 py-2 text-sm hover:bg-accent-tint hover:border-rule-2"
                >
                  <ArrowLeft className="h-3.5 w-3.5" />
                  Back to datasets
                </Link>
              }
            />
          )}
          {datasets.length > 0 && (
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
              {datasets.map((d, i) => (
                <div
                  key={d.slug}
                  className="animate-fade-up"
                  style={{ animationDelay: `${i * 50}ms` }}
                >
                  <DatasetCard dataset={d} />
                </div>
              ))}
            </div>
          )}
        </Container>
      </section>
    </>
  );
}
