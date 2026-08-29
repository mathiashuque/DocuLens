import { z } from "zod";

/**
 * Runtime contract for the completed analysis representation returned by
 * `POST /api/documents/{id}/analysis` and `GET /api/documents/{id}/analysis`.
 * Mirrors `apps/api/app/schemas/analysis.py`. Backend JSON is untrusted input
 * even within this repository: parsing here is the single source of truth
 * for both the runtime check and the inferred TypeScript type.
 *
 * A response whose top-level `extractor` contradicts its
 * `specialized_analysis` discriminator (e.g. `extractor: "generic"` carrying
 * contract fields) fails parsing via the trailing `superRefine` below.
 */

export const documentTypeSchema = z.enum([
  "contract",
  "technical_specification",
  "generic",
]);
export type DocumentType = z.infer<typeof documentTypeSchema>;

export const extractorSchema = z.enum([
  "generic",
  "contract_terms",
  "technical_specification_requirements",
]);
export type Extractor = z.infer<typeof extractorSchema>;

export const levelSchema = z.enum(["low", "medium", "high", "critical"]);
export type Level = z.infer<typeof levelSchema>;

export const prioritySchema = z.enum(["must", "should", "may", "unspecified"]);
export type Priority = z.infer<typeof prioritySchema>;

export const constraintCategorySchema = z.enum([
  "technology",
  "performance",
  "deployment",
  "compatibility",
]);
export type ConstraintCategory = z.infer<typeof constraintCategorySchema>;

const confidenceSchema = z.number().finite().min(0).max(1);
const positivePageSchema = z.number().int().positive();
const uuidSchema = z.uuid();

export const analysisSummarySchema = z.object({
  title: z.string().nullable(),
  purpose: z.string(),
  summary: z.string(),
  key_topics: z.array(z.string()),
});
export type AnalysisSummary = z.infer<typeof analysisSummarySchema>;

export const findingSchema = z.object({
  id: uuidSchema,
  title: z.string(),
  description: z.string(),
  category: z.string(),
  importance: levelSchema,
  source_page: positivePageSchema,
  evidence: z.string(),
  confidence: confidenceSchema,
});
export type Finding = z.infer<typeof findingSchema>;

export const importantDateSchema = z.object({
  id: uuidSchema,
  label: z.string(),
  raw_value: z.string(),
  normalized_date: z.string().nullable(),
  source_page: positivePageSchema,
  evidence: z.string(),
  confidence: confidenceSchema,
});
export type ImportantDate = z.infer<typeof importantDateSchema>;

export const riskEvidenceSchema = z.object({
  page: positivePageSchema,
  text: z.string(),
});
export type RiskEvidence = z.infer<typeof riskEvidenceSchema>;

export const riskSchema = z.object({
  id: uuidSchema,
  title: z.string(),
  description: z.string(),
  category: z.string(),
  severity: levelSchema,
  evidence: z.array(riskEvidenceSchema).min(1),
  confidence: confidenceSchema,
});
export type Risk = z.infer<typeof riskSchema>;

// --- Contract specialized shape ---

export const partySchema = z.object({
  id: uuidSchema,
  name: z.string(),
  role: z.string().nullable(),
  source_page: positivePageSchema,
  evidence: z.string(),
  confidence: confidenceSchema,
});
export type Party = z.infer<typeof partySchema>;

export const obligationSchema = z.object({
  id: uuidSchema,
  obligated_party: z.string().nullable(),
  description: z.string(),
  beneficiary: z.string().nullable(),
  conditions: z.array(z.string()),
  source_page: positivePageSchema,
  evidence: z.string(),
  confidence: confidenceSchema,
});
export type Obligation = z.infer<typeof obligationSchema>;

export const paymentTermSchema = z.object({
  id: uuidSchema,
  payer: z.string().nullable(),
  payee: z.string().nullable(),
  amount_text: z.string().nullable(),
  schedule_text: z.string().nullable(),
  source_page: positivePageSchema,
  evidence: z.string(),
  confidence: confidenceSchema,
});
export type PaymentTerm = z.infer<typeof paymentTermSchema>;

export const clauseSchema = z.object({
  id: uuidSchema,
  title: z.string(),
  description: z.string(),
  conditions: z.array(z.string()),
  notice_period_text: z.string().nullable(),
  source_page: positivePageSchema,
  evidence: z.string(),
  confidence: confidenceSchema,
});
export type Clause = z.infer<typeof clauseSchema>;

export const contractAnalysisSchema = z.object({
  type: z.literal("contract"),
  extractor: z.literal("contract_terms"),
  parties: z.array(partySchema),
  obligations: z.array(obligationSchema),
  payment_terms: z.array(paymentTermSchema),
  renewal_terms: z.array(clauseSchema),
  termination_terms: z.array(clauseSchema),
  liability_terms: z.array(clauseSchema),
  confidentiality_terms: z.array(clauseSchema),
});
export type ContractAnalysis = z.infer<typeof contractAnalysisSchema>;

// --- Technical-specification specialized shape ---

export const requirementSchema = z.object({
  id: uuidSchema,
  identifier: z.string().nullable(),
  statement: z.string(),
  priority: prioritySchema,
  actor: z.string().nullable(),
  measurable_criterion: z.string().nullable(),
  source_page: positivePageSchema,
  evidence: z.string(),
  confidence: confidenceSchema,
});
export type Requirement = z.infer<typeof requirementSchema>;

export const technicalConstraintSchema = z.object({
  id: uuidSchema,
  category: constraintCategorySchema,
  statement: z.string(),
  value_text: z.string().nullable(),
  source_page: positivePageSchema,
  evidence: z.string(),
  confidence: confidenceSchema,
});
export type TechnicalConstraint = z.infer<typeof technicalConstraintSchema>;

export const technicalDependencySchema = z.object({
  id: uuidSchema,
  name: z.string(),
  dependency_type: z.string().nullable(),
  description: z.string(),
  source_page: positivePageSchema,
  evidence: z.string(),
  confidence: confidenceSchema,
});
export type TechnicalDependency = z.infer<typeof technicalDependencySchema>;

export const technicalSpecAnalysisSchema = z.object({
  type: z.literal("technical_specification"),
  extractor: z.literal("technical_specification_requirements"),
  functional_requirements: z.array(requirementSchema),
  non_functional_requirements: z.array(requirementSchema),
  security_requirements: z.array(requirementSchema),
  integration_requirements: z.array(requirementSchema),
  constraints: z.array(technicalConstraintSchema),
  dependencies: z.array(technicalDependencySchema),
});
export type TechnicalSpecAnalysis = z.infer<typeof technicalSpecAnalysisSchema>;

export const specializedAnalysisSchema = z
  .discriminatedUnion("type", [contractAnalysisSchema, technicalSpecAnalysisSchema])
  .nullable();
export type SpecializedAnalysis = z.infer<typeof specializedAnalysisSchema>;

export const analysisSchema = z
  .object({
    id: uuidSchema,
    document_id: uuidSchema,
    document_type: documentTypeSchema,
    extractor: extractorSchema,
    status: z.literal("completed"),
    summary: analysisSummarySchema,
    findings: z.array(findingSchema),
    important_dates: z.array(importantDateSchema),
    risks: z.array(riskSchema),
    specialized_analysis: specializedAnalysisSchema,
    provider: z.string(),
    model: z.string(),
    created_at: z.iso.datetime({ offset: true, local: true }),
  })
  .superRefine((analysis, ctx) => {
    const specialized = analysis.specialized_analysis;
    if (analysis.extractor === "generic") {
      if (specialized !== null) {
        ctx.addIssue({
          code: "custom",
          message: "A generic extractor must not carry a specialized analysis.",
          path: ["specialized_analysis"],
        });
      }
      return;
    }

    if (analysis.extractor === "contract_terms") {
      if (specialized === null || specialized.type !== "contract") {
        ctx.addIssue({
          code: "custom",
          message: "The contract_terms extractor must carry a contract specialized analysis.",
          path: ["specialized_analysis"],
        });
      }
      return;
    }

    if (specialized === null || specialized.type !== "technical_specification") {
      ctx.addIssue({
        code: "custom",
        message:
          "The technical_specification_requirements extractor must carry a technical_specification specialized analysis.",
        path: ["specialized_analysis"],
      });
    }
  });
export type Analysis = z.infer<typeof analysisSchema>;

export function parseAnalysis(data: unknown) {
  return analysisSchema.safeParse(data);
}
