import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));

describe("DocumentLoading", () => {
  it("communicates loading honestly without fake document content or a percentage, in English", async () => {
    vi.doMock("next/root-params", () => ({ lang: async () => "en" }));
    vi.resetModules();
    const DocumentLoading = (await import("@/app/[lang]/documents/[documentId]/loading")).default;

    render(await DocumentLoading());

    expect(screen.getByRole("status")).toHaveTextContent("Loading document…");
    expect(screen.queryByText(/%/)).not.toBeInTheDocument();
  });

  it("uses the root-params locale when preparing the Spanish loading state", async () => {
    vi.doMock("next/root-params", () => ({ lang: async () => "es" }));
    vi.resetModules();
    const DocumentLoading = (await import("@/app/[lang]/documents/[documentId]/loading")).default;

    render(await DocumentLoading());

    expect(screen.getByRole("status")).toHaveTextContent("Cargando documento…");
  });
});
