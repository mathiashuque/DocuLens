import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import { AskDocuLens } from "@/components/questions/AskDocuLens";
import en from "@/lib/i18n/dictionaries/en";
import { mockPrefersReducedMotion } from "../../test-utils/reduced-motion";

const DOCUMENT_ID = "5c68e652-ab9d-442d-a5b3-d24b015155ad";
const citationId = "1a5501f3-425d-4d34-b7e2-7db61e37351e";
const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });

/**
 * Motion's underlying reduced-motion check is a module-level singleton that
 * reads `matchMedia` once, lazily, on first use, so this lives in its own
 * file/module registry and mocks "reduce" before anything here renders a
 * motion component (see `tests/components/motion/primitives-reduced-motion.test.tsx`).
 */
beforeAll(() => {
  mockPrefersReducedMotion(true);
});

describe("AskDocuLens under prefers-reduced-motion: reduce", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("renders example prompts and answers immediately with no animated entrance offset", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(json(200, { document_id: DOCUMENT_ID, status: "completed" }))
      .mockResolvedValueOnce(json(200, {
        document_id: DOCUMENT_ID, question: "What applies?", status: "answered", answer: "The policy applies.",
        citations: [{ chunk_id: citationId, page: 1, evidence: "text" }],
      }));
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<AskDocuLens documentId={DOCUMENT_ID} documentStatus="parsed" documentPageNumbers={[1]} dict={en} lang="en" />);

    const examplePrompt = await screen.findByRole("button", { name: "Summarize this document" });
    expect(examplePrompt.style.opacity).not.toBe("0");

    await user.type(screen.getByLabelText("Ask anything about this document"), "What applies?");
    await user.click(screen.getByRole("button", { name: "Send question" }));

    const answer = await screen.findByText("The policy applies.");
    expect(answer.closest<HTMLElement>('[style]')?.style.opacity ?? "1").not.toBe("0");
  });
});
