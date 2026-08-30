import type { QuestionResponse } from "@/lib/question-schema";

export type Turn = {
  id: string;
  question: string;
} & (
  | { status: "pending" }
  | { status: "answered" | "insufficient_evidence"; result: QuestionResponse }
  | { status: "error"; message: string }
);
