"""Pure, deterministic validation of a classification candidate's evidence.

Runs after Pydantic/taxonomy validation and before thresholding/persistence.
Never repairs a quote semantically and never accepts a paraphrase: every
evidence quote must appear verbatim (after one conservative whitespace
normalization) on the physical page it cites.
"""

import re
from dataclasses import dataclass

from agent.classification.types import (
    ClassificationCandidate,
    ClassificationEvidenceItem,
)

_WHITESPACE_RUN = re.compile(r"\s+")


def normalize_whitespace(text: str) -> str:
    """Collapse any run of whitespace to a single space and strip the ends.

    This is the one documented, conservative normalization evidence matching
    permits: it tolerates line-wrap/CR-LF/multi-space differences between a
    quote and its source page but never touches the wording itself.
    """
    return _WHITESPACE_RUN.sub(" ", text).strip()


@dataclass(frozen=True)
class EvidenceValidationResult:
    valid: bool
    errors: tuple[str, ...]
    deduplicated_evidence: tuple[ClassificationEvidenceItem, ...]


def validate_evidence(
    candidate: ClassificationCandidate, pages: dict[int, str]
) -> EvidenceValidationResult:
    """Validate `candidate.evidence` against persisted original page text.

    `pages` maps physical page number to that page's exact persisted text.
    """
    errors: list[str] = []
    seen: set[tuple[int, str]] = set()
    deduplicated: list[ClassificationEvidenceItem] = []

    for item in candidate.evidence:
        page_text = pages.get(item.page)
        if page_text is None:
            errors.append(f"evidence cites page {item.page}, which does not exist")
            continue

        normalized_quote = normalize_whitespace(item.text)
        normalized_page = normalize_whitespace(page_text)
        if not normalized_quote:
            errors.append(f"evidence quote on page {item.page} is empty")
            continue
        if normalized_quote not in normalized_page:
            errors.append(
                f"evidence quote on page {item.page} does not appear on that page"
            )
            continue

        dedupe_key = (item.page, normalized_quote)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        deduplicated.append(item)

    if not deduplicated and not errors:
        errors.append("no evidence items remained after validation")

    return EvidenceValidationResult(
        valid=not errors,
        errors=tuple(errors),
        deduplicated_evidence=tuple(deduplicated),
    )
