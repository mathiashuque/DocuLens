import { z } from "zod";

export const MAX_QUESTION_LENGTH = 2000;

export const questionRequestSchema = z.object({
  question: z.string().trim().min(1).max(MAX_QUESTION_LENGTH),
}).strict();
export type QuestionRequest = z.infer<typeof questionRequestSchema>;

const citationSchema = z.object({
  chunk_id: z.uuid(),
  page: z.number().int().positive(),
  evidence: z.string().trim().min(1),
});
export type QuestionCitation = z.infer<typeof citationSchema>;

const answeredQuestionSchema = z.object({
  document_id: z.uuid(),
  question: z.string().trim().min(1),
  status: z.literal("answered"),
  answer: z.string().trim().min(1),
  citations: z.array(citationSchema).min(1),
});

const insufficientEvidenceQuestionSchema = z.object({
  document_id: z.uuid(),
  question: z.string().trim().min(1),
  status: z.literal("insufficient_evidence"),
  answer: z.string().trim().min(1),
  citations: z.array(citationSchema).length(0),
});

export const questionResponseSchema = z.discriminatedUnion("status", [
  answeredQuestionSchema,
  insufficientEvidenceQuestionSchema,
]);
export type QuestionResponse = z.infer<typeof questionResponseSchema>;

/** Only the readiness fields the browser needs from the indexing endpoint. */
export const indexResponseSchema = z.object({
  document_id: z.uuid(),
  status: z.literal("completed"),
});
export type IndexResponse = z.infer<typeof indexResponseSchema>;

export function parseQuestionResponseForDocument(documentId: string, data: unknown) {
  const result = questionResponseSchema.safeParse(data);
  if (!result.success || result.data.document_id !== documentId) {
    return { success: false as const };
  }
  return { success: true as const, data: result.data };
}

export function parseIndexResponseForDocument(documentId: string, data: unknown) {
  const result = indexResponseSchema.safeParse(data);
  if (!result.success || result.data.document_id !== documentId) {
    return { success: false as const };
  }
  return { success: true as const, data: result.data };
}
