"""Extractor identity and bounded vocabularies for the contract extractor.

`CONTRACT_EXTRACTOR` is what the API and persistence layers record as
`extractor` when a document's validated classification is `contract`.
"""

from typing import Final, Literal, get_args

CONTRACT_EXTRACTOR: Final[str] = "contract_terms"

ClauseCategory = Literal["renewal", "termination", "liability", "confidentiality"]
ALLOWED_CLAUSE_CATEGORIES: Final[tuple[ClauseCategory, ...]] = get_args(ClauseCategory)
