import type { Analysis } from "./analysis-schema";

/**
 * Every physical page cited as evidence anywhere in an analysis, deduplicated.
 * The Zod schema only proves each `source_page`/risk-evidence page is a
 * positive integer; it cannot know which pages actually exist on the
 * document being viewed, so callers must check the result against the
 * loaded document's page numbers before rendering any evidence link.
 */
export function getCitedPages(analysis: Analysis): number[] {
  const pages = new Set<number>();

  for (const finding of analysis.findings) {
    pages.add(finding.source_page);
  }
  for (const date of analysis.important_dates) {
    pages.add(date.source_page);
  }
  for (const risk of analysis.risks) {
    for (const evidence of risk.evidence) {
      pages.add(evidence.page);
    }
  }

  const specialized = analysis.specialized_analysis;
  if (specialized?.type === "contract") {
    for (const party of specialized.parties) pages.add(party.source_page);
    for (const obligation of specialized.obligations) pages.add(obligation.source_page);
    for (const term of specialized.payment_terms) pages.add(term.source_page);
    for (const clause of [
      ...specialized.renewal_terms,
      ...specialized.termination_terms,
      ...specialized.liability_terms,
      ...specialized.confidentiality_terms,
    ]) {
      pages.add(clause.source_page);
    }
  } else if (specialized?.type === "technical_specification") {
    for (const requirement of [
      ...specialized.functional_requirements,
      ...specialized.non_functional_requirements,
      ...specialized.security_requirements,
      ...specialized.integration_requirements,
    ]) {
      pages.add(requirement.source_page);
    }
    for (const constraint of specialized.constraints) pages.add(constraint.source_page);
    for (const dependency of specialized.dependencies) pages.add(dependency.source_page);
  }

  return [...pages];
}

/**
 * True only when every page the analysis cites as evidence exists in the
 * currently loaded document. A mismatch means the analysis cannot be
 * trusted to render safe evidence links and must be treated as invalid.
 */
export function analysisPagesExistIn(
  analysis: Analysis,
  documentPageNumbers: readonly number[]
): boolean {
  const existing = new Set(documentPageNumbers);
  return getCitedPages(analysis).every((page) => existing.has(page));
}

/** Stable, page-number-derived anchor id for a physical page section. */
export function pageAnchorId(pageNumber: number): string {
  return `page-${pageNumber}`;
}
