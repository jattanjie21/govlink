import { useParams, Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { Container } from "@/components/Container";
import { Breadcrumbs } from "@/components/Breadcrumbs";
import { DatasetCard } from "@/components/DatasetCard";
import { Eyebrow } from "@/components/Eyebrow";
import { EmptyState, ErrorState, LoadingCardGrid } from "@/components/States";
import { useDatasets } from "@/lib/queries";
import { slugify } from "@/lib/utils";

export default function Institution() {
  const { institutionSlug } = useParams<{ institutionSlug: string }>();
  const { data, isLoading, isError, error } = useDatasets();

  const datasets = data
    ? data.filter((d) => slugify(d.publisher) === institutionSlug)
    : [];
  const publisher = datasets[0]?.publisher ?? "";
  const notFound = !!data && datasets.length === 0;

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
          <h1 className="mt-4 font-display text-xl font-normal leading-tight tracking-tight">
            {publisher || "Unknown institution"}
          </h1>
          {data && !notFound && (
            <p className="mt-3 text-sm text-ink-3">
              <span className="num text-ink">{datasets.length}</span>{" "}
              {datasets.length === 1 ? "dataset" : "datasets"} from this
              publisher.
            </p>
          )}
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
              {datasets.map((d) => (
                <DatasetCard key={d.slug} dataset={d} />
              ))}
            </div>
          )}
        </Container>
      </section>
    </>
  );
}
