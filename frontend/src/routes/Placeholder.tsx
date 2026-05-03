import { Container } from "@/components/Container";

interface PlaceholderProps {
  title: string;
  step: string;
}

export default function Placeholder({ title, step }: PlaceholderProps) {
  return (
    <Container>
      <section className="py-24">
        <p className="text-eyebrow uppercase text-ink-3">{step}</p>
        <h1 className="mt-6 font-display text-xl tracking-tight">{title}</h1>
        <p className="mt-3 text-sm text-ink-2">Lands in a later step.</p>
      </section>
    </Container>
  );
}
