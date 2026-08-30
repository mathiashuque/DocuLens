import { z } from "zod";

/**
 * Runtime contract for the durable document representation returned by
 * `POST /api/documents` and `GET /api/documents/{id}`. Backend JSON is
 * untrusted input even within this repository: parsing here is the single
 * source of truth for both the runtime check and the inferred TypeScript type.
 */

export const documentStatusSchema = z.enum(["parsed", "ocr_required"]);
export type DocumentStatus = z.infer<typeof documentStatusSchema>;

export const documentPageSchema = z.object({
  page_number: z.number().int().positive(),
  text: z.string(),
});
export type DocumentPage = z.infer<typeof documentPageSchema>;

export const documentSectionSchema = z
  .object({
    id: z.uuid(),
    title: z.string().min(1),
    level: z.number().int().positive(),
    parent_section_id: z.uuid().nullable(),
    page_start: z.number().int().positive(),
    page_end: z.number().int().positive(),
    section_path: z.array(z.string().min(1)).min(1),
    text: z.string(),
  })
  .refine((section) => section.page_end >= section.page_start, {
    message: "page_end must be greater than or equal to page_start",
    path: ["page_end"],
  });
export type DocumentSection = z.infer<typeof documentSectionSchema>;

export const documentSchema = z.object({
  id: z.uuid(),
  filename: z.string().min(1),
  content_hash: z.string().regex(/^[0-9a-f]{64}$/),
  status: documentStatusSchema,
  page_count: z.number().int().positive(),
  created_at: z.iso.datetime({ offset: true, local: true }),
  pages: z.array(documentPageSchema),
  sections: z.array(documentSectionSchema),
  demo_slug: z.string().min(1).nullable().optional(),
  demo_title: z.string().min(1).nullable().optional(),
  demo_description: z.string().min(1).nullable().optional(),
  demo_document_type: z.enum(["contract", "technical_specification", "generic"]).nullable().optional(),
  demo_questions: z.array(z.object({
    id: z.string().min(1),
    question: z.string().min(1),
    status: z.enum(["answered", "insufficient_evidence"]),
    answer: z.string().min(1),
    citations: z.array(z.object({
      chunk_id: z.uuid(), page: z.number().int().positive(), evidence: z.string().min(1),
    })),
  })).nullable().optional(),
});
export type Document = z.infer<typeof documentSchema>;

export function parseDocument(data: unknown) {
  return documentSchema.safeParse(data);
}
