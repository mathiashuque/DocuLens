import { render, screen } from "@testing-library/react";
import { beforeAll, describe, expect, it } from "vitest";

import { Reveal, StaggerGroup, StaggerItem } from "@/components/motion/primitives";
import { mockPrefersReducedMotion } from "../../test-utils/reduced-motion";

/**
 * Motion's underlying reduced-motion check is a module-level singleton that
 * reads `matchMedia` once, lazily, on first use — it will not react to a
 * mock applied after some earlier test already triggered it. So this file
 * mocks "reduce" before anything in it ever renders a motion component, and
 * contains only reduced-motion assertions (see primitives.test.tsx for the
 * normal-motion behavior, in its own file/module registry).
 */
beforeAll(() => {
  mockPrefersReducedMotion(true);
});

describe("Reveal under prefers-reduced-motion: reduce", () => {
  it("renders children immediately with no entrance offset", () => {
    render(<Reveal>Reduced motion copy</Reveal>);
    const node = screen.getByText("Reduced motion copy");
    expect(node).toBeInTheDocument();
    expect(node.style.opacity).not.toBe("0");
  });
});

describe("StaggerGroup / StaggerItem under prefers-reduced-motion: reduce", () => {
  it("keeps every item visible immediately, without a staggered entrance", () => {
    render(
      <StaggerGroup as="ul">
        <StaggerItem as="li">Alpha</StaggerItem>
        <StaggerItem as="li">Beta</StaggerItem>
      </StaggerGroup>
    );
    expect(screen.getByText("Alpha").style.opacity).not.toBe("0");
    expect(screen.getByText("Beta").style.opacity).not.toBe("0");
  });
});
