import { describe, expect, it } from "vitest";

import { analysisPagesExistIn, getCitedPages, pageAnchorId } from "@/lib/analysis-evidence";
import { parseAnalysis, type Analysis } from "@/lib/analysis-schema";

function analysisWith(overrides: Record<string, unknown>): Analysis {
  const payload = {
    id: "5c68e652-ab9d-442d-a5b3-d24b015155ad",
    document_id: "5c68e652-ab9d-442d-a5b3-d24b015155ad",
    document_type: "generic",
    extractor: "generic",
    status: "completed",
    summary: { title: null, purpose: "p", summary: "s", key_topics: [] },
    findings: [],
    important_dates: [],
    risks: [],
    specialized_analysis: null,
    provider: "openai",
    model: "gpt-4o-mini",
    created_at: "2026-08-29T12:34:56+00:00",
    ...overrides,
  };
  const result = parseAnalysis(payload);
  if (!result.success) {
    throw new Error("test fixture is not a valid analysis payload");
  }
  return result.data;
}

describe("pageAnchorId", () => {
  it("derives a stable anchor id from a page number", () => {
    expect(pageAnchorId(7)).toBe("page-7");
  });
});

describe("getCitedPages", () => {
  it("collects pages from findings, dates, and multi-page risk evidence", () => {
    const analysis = analysisWith({
      findings: [
        {
          id: "5c68e652-ab9d-442d-a5b3-d24b015155ad",
          title: "t",
          description: "d",
          category: "c",
          importance: "low",
          source_page: 1,
          evidence: "e",
          confidence: 0.5,
        },
      ],
      important_dates: [
        {
          id: "5c68e652-ab9d-442d-a5b3-d24b015155ad",
          label: "l",
          raw_value: "r",
          normalized_date: null,
          source_page: 2,
          evidence: "e",
          confidence: 0.5,
        },
      ],
      risks: [
        {
          id: "5c68e652-ab9d-442d-a5b3-d24b015155ad",
          title: "t",
          description: "d",
          category: "c",
          severity: "low",
          evidence: [
            { page: 3, text: "e1" },
            { page: 4, text: "e2" },
          ],
          confidence: 0.5,
        },
      ],
    });

    expect(getCitedPages(analysis).sort()).toEqual([1, 2, 3, 4]);
  });

  it("collects pages from a contract specialized analysis", () => {
    const analysis = analysisWith({
      document_type: "contract",
      extractor: "contract_terms",
      specialized_analysis: {
        type: "contract",
        extractor: "contract_terms",
        parties: [
          {
            id: "5c68e652-ab9d-442d-a5b3-d24b015155ad",
            name: "n",
            role: null,
            source_page: 5,
            evidence: "e",
            confidence: 0.5,
          },
        ],
        obligations: [],
        payment_terms: [],
        renewal_terms: [
          {
            id: "5c68e652-ab9d-442d-a5b3-d24b015155ad",
            title: "t",
            description: "d",
            conditions: [],
            notice_period_text: null,
            source_page: 6,
            evidence: "e",
            confidence: 0.5,
          },
        ],
        termination_terms: [],
        liability_terms: [],
        confidentiality_terms: [],
      },
    });

    expect(getCitedPages(analysis).sort()).toEqual([5, 6]);
  });

  it("collects pages from a technical-specification specialized analysis", () => {
    const analysis = analysisWith({
      document_type: "technical_specification",
      extractor: "technical_specification_requirements",
      specialized_analysis: {
        type: "technical_specification",
        extractor: "technical_specification_requirements",
        functional_requirements: [
          {
            id: "5c68e652-ab9d-442d-a5b3-d24b015155ad",
            identifier: null,
            statement: "s",
            priority: "unspecified",
            actor: null,
            measurable_criterion: null,
            source_page: 7,
            evidence: "e",
            confidence: 0.5,
          },
        ],
        non_functional_requirements: [],
        security_requirements: [],
        integration_requirements: [],
        constraints: [
          {
            id: "5c68e652-ab9d-442d-a5b3-d24b015155ad",
            category: "technology",
            statement: "s",
            value_text: null,
            source_page: 8,
            evidence: "e",
            confidence: 0.5,
          },
        ],
        dependencies: [],
      },
    });

    expect(getCitedPages(analysis).sort()).toEqual([7, 8]);
  });
});

describe("analysisPagesExistIn", () => {
  it("is true when every cited page exists on the document", () => {
    const analysis = analysisWith({
      findings: [
        {
          id: "5c68e652-ab9d-442d-a5b3-d24b015155ad",
          title: "t",
          description: "d",
          category: "c",
          importance: "low",
          source_page: 2,
          evidence: "e",
          confidence: 0.5,
        },
      ],
    });

    expect(analysisPagesExistIn(analysis, [1, 2, 3])).toBe(true);
  });

  it("is false when a cited page does not exist on the document", () => {
    const analysis = analysisWith({
      findings: [
        {
          id: "5c68e652-ab9d-442d-a5b3-d24b015155ad",
          title: "t",
          description: "d",
          category: "c",
          importance: "low",
          source_page: 99,
          evidence: "e",
          confidence: 0.5,
        },
      ],
    });

    expect(analysisPagesExistIn(analysis, [1, 2, 3])).toBe(false);
  });

  it("is true for an analysis with no cited pages", () => {
    const analysis = analysisWith({});

    expect(analysisPagesExistIn(analysis, [])).toBe(true);
  });
});
