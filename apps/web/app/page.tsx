import type { Metadata } from "next";

import { UploadForm } from "@/components/UploadForm";
import { UsageAllowance } from "@/components/UsageAllowance";
import { Reveal, StaggerGroup, StaggerItem } from "@/components/motion/primitives";
import { getSiteUrl } from "@/lib/site-config";

export const metadata: Metadata = {
  alternates: {
    canonical: "/",
  },
};

const jsonLd = {
  "@context": "https://schema.org",
  "@type": "WebApplication",
  name: "DocuLens",
  url: getSiteUrl(),
  description:
    "Upload a PDF, then ask it questions or request analysis grounded in the exact page and quote it came from.",
  applicationCategory: "BusinessApplication",
  operatingSystem: "Any (web browser)",
};

const STEPS = [
  {
    step: "1",
    title: "Upload",
    description: "Drop in a PDF. It's prepared for grounded questions automatically.",
  },
  {
    step: "2",
    title: "Ask or analyze",
    description: "Ask a direct question, or request analysis — risks, obligations, deadlines, comparisons, summaries.",
  },
  {
    step: "3",
    title: "Read the evidence",
    description: "Every answer cites the exact page and quote it came from, or says so when it can't.",
  },
];

export default function HomePage() {
  return (
    <div className="flex flex-1 flex-col items-center px-6 py-16 sm:py-20">
      <script
        type="application/ld+json"
        // Static, trusted marketing fields only — never uploaded-document or
        // user-controlled values. `<` is escaped per Next.js guidance for
        // safely embedding JSON in a script tag.
        dangerouslySetInnerHTML={{
          __html: JSON.stringify(jsonLd).replace(/</g, "\\u003c"),
        }}
      />
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
        <StaggerGroup as="ul" className="grid gap-6 sm:grid-cols-3">
          {STEPS.map((item) => (
            <StaggerItem as="li" key={item.step}>
              <div className="flex h-full flex-col gap-1.5 border-t-2 border-accent/25 pt-3">
                <p className="text-xs font-semibold tracking-wide text-accent-strong">
                  Step {item.step}
                </p>
                <p className="text-sm font-semibold text-ink">{item.title}</p>
                <p className="text-sm leading-6 text-ink-muted">{item.description}</p>
              </div>
            </StaggerItem>
          ))}
        </StaggerGroup>
      </Reveal>
    </div>
  );
}

/**
 * Decorative conversation/evidence preview built from semantic HTML/CSS —
 * never a screenshot of a real document, and never a fabricated confidence
 * score, since the product doesn't expose calibrated confidence.
 */
function EvidenceMotif() {
  return (
    <div aria-hidden="true" className="flex flex-col gap-3 rounded-card border border-hairline bg-surface p-5 shadow-card">
      <div className="ml-auto max-w-[80%] rounded-card bg-accent px-3.5 py-2 text-xs text-white">
        What happens if either party wants to end this early?
      </div>
      <div className="flex items-start gap-2">
        <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-accent-soft text-[9px] font-semibold text-accent-strong">
          DL
        </span>
        <div className="flex flex-col gap-2">
          <div className="h-2 w-40 rounded-full bg-canvas-strong" />
          <div className="h-2 w-32 rounded-full bg-canvas-strong" />
          <div className="mt-1 flex flex-col gap-1 rounded-md border-y border-r border-l-2 border-hairline border-l-accent bg-accent-soft/40 px-3 py-2">
            <span className="text-[10px] font-medium text-ink-subtle">Page 12</span>
            <span className="text-xs leading-5 text-ink-muted italic">
              &ldquo;&hellip;either party may terminate with sixty days&rsquo;
              written notice&hellip;&rdquo;
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
