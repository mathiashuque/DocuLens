import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Reveal, StaggerGroup, StaggerItem } from "@/components/motion/primitives";

describe("Reveal", () => {
  it("renders children immediately", () => {
    render(<Reveal>Hero copy</Reveal>);
    expect(screen.getByText("Hero copy")).toBeInTheDocument();
  });
});

describe("StaggerGroup / StaggerItem", () => {
  it("renders every item immediately", () => {
    render(
      <StaggerGroup as="ul">
        <StaggerItem as="li">First</StaggerItem>
        <StaggerItem as="li">Second</StaggerItem>
        <StaggerItem as="li">Third</StaggerItem>
      </StaggerGroup>
    );
    expect(screen.getByText("First")).toBeInTheDocument();
    expect(screen.getByText("Second")).toBeInTheDocument();
    expect(screen.getByText("Third")).toBeInTheDocument();
  });
});
