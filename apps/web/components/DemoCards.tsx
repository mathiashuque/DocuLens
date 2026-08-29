import Link from "next/link";

import type { DemoCard } from "@/lib/demo-schema";

export function DemoCards({ demos }: { demos: DemoCard[] }) {
  return (
    <section aria-labelledby="examples-heading" className="mt-12 w-full max-w-4xl">
      <h2 id="examples-heading" className="text-xl font-semibold text-zinc-900">Try an example</h2>
      <p className="mt-2 text-sm text-zinc-600">Explore synthetic, precomputed documents without using provider quota.</p>
      {demos.length === 3 ? (
        <ul className="mt-5 grid gap-4 md:grid-cols-3">
          {demos.map((demo) => (
            <li key={demo.slug} className="rounded-lg border border-zinc-200 bg-white p-5">
              <p className="text-xs font-semibold uppercase tracking-wide text-zinc-500">{demo.document_type.replaceAll("_", " ")}</p>
              <h3 className="mt-2 font-semibold text-zinc-900">{demo.title}</h3>
              <p className="mt-2 text-sm text-zinc-600">{demo.description}</p>
              <Link href={`/documents/${demo.document_id}`} className="mt-4 inline-block text-sm font-semibold text-zinc-900 underline underline-offset-2 focus-visible:outline focus-visible:outline-2">Open demo</Link>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-4 rounded-md border border-zinc-200 bg-zinc-50 p-4 text-sm text-zinc-600">Examples are not available right now. You can still upload a document above.</p>
      )}
    </section>
  );
}
