import { z } from "zod";

export const usageResponseSchema = z.object({
  enforced: z.boolean(),
  allowances: z.array(z.object({
    category: z.enum(["analysis", "index", "question"]),
    limit: z.number().int().positive(),
    remaining: z.number().int().nonnegative(),
    retry_at: z.string().datetime().nullable(),
  })),
});

export type UsageResponse = z.infer<typeof usageResponseSchema>;
