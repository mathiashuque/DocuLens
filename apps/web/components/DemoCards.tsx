import Link from "next/link";

import { StaggerGroup, StaggerItem } from "@/components/motion/primitives";
import type { DemoCard } from "@/lib/demo-schema";

const TYPE_ACCENTS: Record<DemoCard["document_type"], string> = {
  contract: "bg-accent-soft text-accent-strong",
  technical_specification: "bg-cyan-soft text-cyan",
  generic: "bg-canvas-strong text-ink-muted",
};

export function DemoCards({ demos }: { demos: DemoCard[] }) {
  return (
    <section aria-labelledby="examples-heading" className="w-full max-w-4xl">
      <h2 id="examples-heading" className="text-xl font-semibold text-ink">Try an example</h2>
      <p className="mt-2 text-sm text-ink-muted">Explore synthetic, precomputed documents without using provider quota.</p>
      {demos.length === 3 ? (
        <StaggerGroup as="ul" className="mt-5 grid gap-4 md:grid-cols-3">
          {demos.map((demo) => (
            <StaggerItem as="li" key={demo.slug}>
              <div className="group relative h-full rounded-card border border-hairline bg-surface p-5 shadow-card transition-shadow motion-safe:hover:shadow-card-hover">
                <p
                  className={`inline-flex items-center rounded-chip px-2 py-0.5 text-xs font-semibold uppercase tracking-wide ${TYPE_ACCENTS[demo.document_type]}`}
                >
                  {demo.document_type.replaceAll("_", " ")}
                </p>
                <h3 className="mt-3 font-semibold text-ink">{demo.title}</h3>
                <p className="mt-2 text-sm text-ink-muted">{demo.description}</p>
                <Link
                  href={`/documents/${demo.document_id}`}
                  className="mt-4 inline-block text-sm font-semibold text-accent underline underline-offset-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent after:absolute after:inset-0"
                >
                  Open demo
                </Link>
              </div>
            </StaggerItem>
          ))}
        </StaggerGroup>
      ) : (
        <p className="mt-4 rounded-card border border-hairline bg-surface-muted p-4 text-sm text-ink-muted">Examples are not available right now. You can still upload a document above.</p>
      )}
    </section>
  );
}
