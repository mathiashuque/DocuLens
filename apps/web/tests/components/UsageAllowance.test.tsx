import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { UsageAllowance } from "@/components/UsageAllowance";

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), { status: 200, headers: { "content-type": "application/json" } });
}

describe("UsageAllowance", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("renders nothing visible when usage is not enforced", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ enforced: false, allowances: [] })));
    render(<UsageAllowance />);

    await waitFor(() => expect(screen.queryByRole("paragraph")).not.toBeInTheDocument());
  });

  it("shows an understandable label for remaining allowance, not the raw category name", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({
      enforced: true,
      allowances: [{ category: "index", limit: 5, remaining: 3, retry_at: null }],
    })));
    render(<UsageAllowance />);

    expect(await screen.findByText(/3 of 5 free document uploads left today/)).toBeInTheDocument();
  });

  it("shows question allowance only on the document route", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({
      enforced: true,
      allowances: [{ category: "question", limit: 10, remaining: 7, retry_at: null }],
    })));
    render(<UsageAllowance documentId="5c68e652-ab9d-442d-a5b3-d24b015155ad" />);

    expect(await screen.findByText(/7 of 10 free questions left today/)).toBeInTheDocument();
  });

  it("shows an exhausted state with reset information instead of a raw zero count", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({
      enforced: true,
      allowances: [{ category: "question", limit: 10, remaining: 0, retry_at: "2026-08-30T18:00:00Z" }],
    })));
    render(<UsageAllowance documentId="5c68e652-ab9d-442d-a5b3-d24b015155ad" />);

    expect(await screen.findByText(/You've used today's free questions/)).toBeInTheDocument();
  });

  it("fails gracefully and renders nothing when the usage request fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("network down")));
    render(<UsageAllowance />);

    await waitFor(() => expect(screen.queryByText(/free/)).not.toBeInTheDocument());
  });
});
