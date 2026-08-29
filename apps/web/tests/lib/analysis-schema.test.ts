import { describe, expect, it } from "vitest";

import { parseAnalysis } from "@/lib/analysis-schema";

function baseAnalysis(overrides: Record<string, unknown> = {}) {
  return {
    id: "5c68e652-ab9d-442d-a5b3-d24b015155ad",
    document_id: "5c68e652-ab9d-442d-a5b3-d24b015155ad",
    document_type: "generic",
    extractor: "generic",
    status: "completed",
    summary: {
      title: "Quarterly Update",
      purpose: "Explains progress.",
      summary: "A short summary.",
      key_topics: ["migration"],
    },
    findings: [],
    important_dates: [],
    risks: [],
    specialized_analysis: null,
    provider: "openai",
    model: "gpt-4o-mini",
    created_at: "2026-08-29T12:34:56+00:00",
    ...overrides,
  };
}

function validFinding(overrides: Record<string, unknown> = {}) {
  return {
    id: "5c68e652-ab9d-442d-a5b3-d24b015155ad",
    title: "Key point",
    description: "An important point.",
    category: "general",
    importance: "medium",
    source_page: 1,
    evidence: "quoted text",
    confidence: 0.8,
    ...overrides,
  };
}

function validRisk(overrides: Record<string, unknown> = {}) {
  return {
    id: "5c68e652-ab9d-442d-a5b3-d24b015155ad",
    title: "Auto-renewal risk",
    description: "d",
    category: "renewal",
    severity: "medium",
    evidence: [{ page: 1, text: "renews automatically" }],
    confidence: 0.6,
    ...overrides,
  };
}

function validContractAnalysis(overrides: Record<string, unknown> = {}) {
  return {
    type: "contract",
    extractor: "contract_terms",
    parties: [
      {
        id: "5c68e652-ab9d-442d-a5b3-d24b015155ad",
        name: "Northstar Hosting Ltd.",
        role: "provider",
        source_page: 1,
        evidence: "Northstar Hosting Ltd.",
        confidence: 0.97,
      },
    ],
    obligations: [],
    payment_terms: [],
    renewal_terms: [],
    termination_terms: [],
    liability_terms: [],
    confidentiality_terms: [],
    ...overrides,
  };
}

function validTechnicalSpecAnalysis(overrides: Record<string, unknown> = {}) {
  return {
    type: "technical_specification",
    extractor: "technical_specification_requirements",
    functional_requirements: [
      {
        id: "5c68e652-ab9d-442d-a5b3-d24b015155ad",
        identifier: "FR-12",
        statement: "Revoke active sessions",
        priority: "must",
        actor: "administrator",
        measurable_criterion: null,
        source_page: 8,
        evidence: "FR-12: The service shall allow administrators to revoke active sessions.",
        confidence: 0.98,
      },
    ],
    non_functional_requirements: [],
    security_requirements: [],
    integration_requirements: [],
    constraints: [],
    dependencies: [],
    ...overrides,
  };
}

describe("parseAnalysis", () => {
  it("parses a valid generic analysis payload", () => {
    const result = parseAnalysis(baseAnalysis({ findings: [validFinding()] }));

    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.findings[0].title).toBe("Key point");
      expect(result.data.specialized_analysis).toBeNull();
    }
  });

  it("parses a valid contract analysis payload", () => {
    const result = parseAnalysis(
      baseAnalysis({
        document_type: "contract",
        extractor: "contract_terms",
        specialized_analysis: validContractAnalysis(),
      })
    );

    expect(result.success).toBe(true);
    if (result.success && result.data.specialized_analysis?.type === "contract") {
      expect(result.data.specialized_analysis.parties[0].name).toBe(
        "Northstar Hosting Ltd."
      );
    }
  });

  it("parses a valid technical-specification analysis payload", () => {
    const result = parseAnalysis(
      baseAnalysis({
        document_type: "technical_specification",
        extractor: "technical_specification_requirements",
        specialized_analysis: validTechnicalSpecAnalysis(),
      })
    );

    expect(result.success).toBe(true);
    if (
      result.success &&
      result.data.specialized_analysis?.type === "technical_specification"
    ) {
      expect(
        result.data.specialized_analysis.functional_requirements[0].identifier
      ).toBe("FR-12");
    }
  });

  it("parses risks with multi-page evidence", () => {
    const result = parseAnalysis(baseAnalysis({ risks: [validRisk()] }));

    expect(result.success).toBe(true);
  });

  it("rejects a malformed top-level id", () => {
    const result = parseAnalysis(baseAnalysis({ id: "not-a-uuid" }));

    expect(result.success).toBe(false);
  });

  it("rejects a malformed created_at date", () => {
    const result = parseAnalysis(baseAnalysis({ created_at: "not-a-date" }));

    expect(result.success).toBe(false);
  });

  it("rejects confidence outside [0, 1]", () => {
    const result = parseAnalysis(
      baseAnalysis({ findings: [validFinding({ confidence: 1.5 })] })
    );

    expect(result.success).toBe(false);
  });

  it("rejects non-finite confidence", () => {
    const result = parseAnalysis(
      baseAnalysis({ findings: [validFinding({ confidence: Number.NaN })] })
    );

    expect(result.success).toBe(false);
  });

  it("rejects a non-positive source page", () => {
    const result = parseAnalysis(
      baseAnalysis({ findings: [validFinding({ source_page: 0 })] })
    );

    expect(result.success).toBe(false);
  });

  it("rejects an invalid importance enum value", () => {
    const result = parseAnalysis(
      baseAnalysis({ findings: [validFinding({ importance: "urgent" })] })
    );

    expect(result.success).toBe(false);
  });

  it("rejects an invalid document_type", () => {
    const result = parseAnalysis(baseAnalysis({ document_type: "invoice" }));

    expect(result.success).toBe(false);
  });

  it("rejects an invalid extractor", () => {
    const result = parseAnalysis(baseAnalysis({ extractor: "unknown_extractor" }));

    expect(result.success).toBe(false);
  });

  it("rejects a risk with zero evidence items", () => {
    const result = parseAnalysis(baseAnalysis({ risks: [validRisk({ evidence: [] })] }));

    expect(result.success).toBe(false);
  });

  it("rejects a generic extractor carrying a contract specialized analysis", () => {
    const result = parseAnalysis(
      baseAnalysis({
        extractor: "generic",
        specialized_analysis: validContractAnalysis(),
      })
    );

    expect(result.success).toBe(false);
  });

  it("rejects a contract_terms extractor with a null specialized analysis", () => {
    const result = parseAnalysis(
      baseAnalysis({
        document_type: "contract",
        extractor: "contract_terms",
        specialized_analysis: null,
      })
    );

    expect(result.success).toBe(false);
  });

  it("rejects a contract_terms extractor carrying a technical_specification specialized analysis", () => {
    const result = parseAnalysis(
      baseAnalysis({
        document_type: "contract",
        extractor: "contract_terms",
        specialized_analysis: validTechnicalSpecAnalysis(),
      })
    );

    expect(result.success).toBe(false);
  });

  it("rejects a technical_specification_requirements extractor with a null specialized analysis", () => {
    const result = parseAnalysis(
      baseAnalysis({
        document_type: "technical_specification",
        extractor: "technical_specification_requirements",
        specialized_analysis: null,
      })
    );

    expect(result.success).toBe(false);
  });

  it("rejects missing required fields", () => {
    const payload: Record<string, unknown> = baseAnalysis();
    delete payload.summary;

    expect(parseAnalysis(payload).success).toBe(false);
  });
});
