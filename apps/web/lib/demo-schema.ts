import { z } from "zod";

export const demoCardSchema = z.object({
  slug: z.string().min(1),
  title: z.string().min(1),
  description: z.string().min(1),
  document_type: z.enum(["contract", "technical_specification", "generic"]),
  page_count: z.number().int().positive(),
  document_id: z.uuid(),
});
export const demoCardsSchema = z.array(demoCardSchema).max(3);
export type DemoCard = z.infer<typeof demoCardSchema>;
