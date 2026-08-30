import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { CuratedDemoQuestions } from "@/components/questions/CuratedDemoQuestions";
import en from "@/lib/i18n/dictionaries/en";

describe("CuratedDemoQuestions", () => {
  it("shows a compact precomputed-demo notice alongside the chat-style questions", () => {
    render(<CuratedDemoQuestions questions={[{
      id: "payment", question: "When is payment due?", status: "answered",
      answer: "On the first business day.",
      citations: [{ chunk_id: "1a5501f3-425d-4d34-b7e2-7db61e37351e", page: 2, evidence: "first business day" }],
    }]} dict={en.questions} />);
    expect(screen.getByText("Precomputed demo")).toBeInTheDocument();
    expect(screen.getByText(/never calls an AI provider/)).toBeInTheDocument();
  });

  it("reveals only an exactly selected precomputed answer with inline page evidence", async () => {
    const user = userEvent.setup();
    render(<CuratedDemoQuestions questions={[{
      id: "payment", question: "When is payment due?", status: "answered",
      answer: "On the first business day.",
      citations: [{ chunk_id: "1a5501f3-425d-4d34-b7e2-7db61e37351e", page: 2, evidence: "first business day" }],
    }]} dict={en.questions} />);
    expect(screen.queryByText("On the first business day.")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "When is payment due?" }));
    expect(screen.getByText("On the first business day.")).toBeInTheDocument();
    expect(screen.getByText("Page 2")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /page 2/i })).not.toBeInTheDocument();
  });

  it("renders insufficient evidence without a citation shell", async () => {
    const user = userEvent.setup();
    render(<CuratedDemoQuestions questions={[{
      id: "missing", question: "What is missing?", status: "insufficient_evidence",
      answer: "The document does not provide enough information.", citations: [],
    }]} dict={en.questions} />);
    await user.click(screen.getByRole("button", { name: "What is missing?" }));
    expect(screen.getByText("Insufficient evidence")).toBeInTheDocument();
    expect(screen.queryByRole("list", { name: "Answer citations" })).not.toBeInTheDocument();
  });
});
