import { UploadForm } from "@/components/UploadForm";
import { DemoCards } from "@/components/DemoCards";
import { UsageAllowance } from "@/components/UsageAllowance";
import { Reveal, StaggerGroup, StaggerItem } from "@/components/motion/primitives";
import { fetchDemos } from "@/lib/demo-client";

const CAPABILITIES = [
  {
    title: "Upload",
    description: "Drop in a PDF. Pages and section structure are preserved from the start.",
  },
  {
    title: "Ask anything",
    description: "Ask direct questions or request analysis — risks, obligations, deadlines, comparisons, summaries.",
  },
  {
    title: "Evidence",
    description: "Every claim links back to the exact page and quote it came from.",
  },
  {
    title: "Grounded answers",
    description: "Every answer is grounded in this document, or reports a clear insufficient-evidence result.",
  },
];

export default async function HomePage() {
  const demos = await fetchDemos();
  return (
    <div className="flex flex-1 flex-col items-center px-6 py-16 sm:py-20">
      <div className="grid w-full max-w-5xl items-start gap-10 lg:grid-cols-[minmax(0,1fr)_22rem] lg:gap-14">
        <Reveal>
          <h1 className="text-3xl font-semibold tracking-tight text-balance text-ink sm:text-4xl lg:text-5xl">
            Understand complex documents with evidence, not guesswork.
          </h1>
          <p className="mt-4 max-w-xl text-base leading-7 text-ink-muted">
            Upload a document, then ask it anything &mdash; factual questions,
            risk analysis, obligation extraction, deadlines, comparisons, or
            summaries. Every answer is grounded in this document and traceable
            back to the exact page and quote it came from.
          </p>

          <div className="mt-8 max-w-xl rounded-card border border-hairline bg-surface p-6 shadow-card">
            <UploadForm />
            <UsageAllowance />
          </div>
        </Reveal>

        <Reveal delay={0.08} className="hidden lg:block">
          <EvidenceMotif />
        </Reveal>
      </div>

      <Reveal delay={0.12} className="mt-14 w-full max-w-5xl">
        <StaggerGroup as="ul" className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {CAPABILITIES.map((capability) => (
            <StaggerItem as="li" key={capability.title}>
              <div className="h-full rounded-card border border-hairline bg-surface p-4">
                <p className="text-sm font-semibold text-ink">{capability.title}</p>
                <p className="mt-1 text-xs leading-5 text-ink-muted">{capability.description}</p>
              </div>
            </StaggerItem>
          ))}
        </StaggerGroup>
      </Reveal>

      <div className="mt-14 w-full max-w-5xl">
        <DemoCards demos={demos} />
      </div>
    </div>
  );
}

/** Decorative evidence-card motif built from semantic HTML/CSS: never a screenshot of a real document. */
function EvidenceMotif() {
  return (
    <div aria-hidden="true" className="rounded-card border border-hairline bg-surface p-5 shadow-card">
      <div className="flex items-center justify-between border-b border-hairline pb-3 text-xs text-ink-subtle">
        <span>Page 12</span>
        <span className="rounded-chip bg-accent-soft px-2 py-0.5 font-medium text-accent-strong">
          Confidence 92%
        </span>
      </div>
      <div className="mt-3 flex flex-col gap-2">
        <div className="h-2 w-11/12 rounded-full bg-canvas-strong" />
        <div className="h-2 w-full rounded-full bg-canvas-strong" />
        <div className="h-2 w-4/5 rounded-full bg-canvas-strong" />
        <div className="mt-3 rounded-md border-l-2 border-accent bg-accent-soft py-2 pl-3 text-xs leading-5 text-ink-muted italic">
          &ldquo;&hellip;shall automatically renew for successive twelve-month
          periods unless either party provides written notice&hellip;&rdquo;
        </div>
        <div className="mt-1 h-2 w-2/3 rounded-full bg-canvas-strong" />
      </div>
    </div>
  );
}
