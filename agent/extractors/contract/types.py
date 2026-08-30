"""Typed structured-output contract produced by the contract extractor
provider, before deterministic validation and ID assignment.
"""

import math

from pydantic import BaseModel, Field, field_validator

from agent.extractors.contract.taxonomy import ClauseCategory

MAX_PARTIES = 10
MAX_OBLIGATIONS = 30
MAX_PAYMENT_TERMS = 15
MAX_CLAUSES = 15
MAX_CONDITIONS = 10


def _finite_unit_interval(value: float) -> float:
    if not math.isfinite(value):
        raise ValueError("confidence must be a finite number")
    if not 0.0 <= value <= 1.0:
        raise ValueError("confidence must be within [0, 1]")
    return value


class PartyCandidate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    role: str | None = Field(default=None, max_length=100)
    source_page: int = Field(gt=0)
    evidence: str = Field(min_length=1, max_length=1000)
    confidence: float

    @field_validator("confidence")
    @classmethod
    def _confidence(cls, value: float) -> float:
        return _finite_unit_interval(value)


class ObligationCandidate(BaseModel):
    obligated_party: str | None = Field(default=None, max_length=200)
    description: str = Field(min_length=1, max_length=1000)
    beneficiary: str | None = Field(default=None, max_length=200)
    conditions: list[str] = Field(default_factory=list, max_length=MAX_CONDITIONS)
    source_page: int = Field(gt=0)
    evidence: str = Field(min_length=1, max_length=1000)
    confidence: float

    @field_validator("confidence")
    @classmethod
    def _confidence(cls, value: float) -> float:
        return _finite_unit_interval(value)

    @field_validator("conditions")
    @classmethod
    def _non_empty_conditions(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item.strip()]


class PaymentTermCandidate(BaseModel):
    payer: str | None = Field(default=None, max_length=200)
    payee: str | None = Field(default=None, max_length=200)
    amount_text: str | None = Field(default=None, max_length=200)
    schedule_text: str | None = Field(default=None, max_length=500)
    source_page: int = Field(gt=0)
    evidence: str = Field(min_length=1, max_length=1000)
    confidence: float

    @field_validator("confidence")
    @classmethod
    def _confidence(cls, value: float) -> float:
        return _finite_unit_interval(value)


class ClauseCandidate(BaseModel):
    category: ClauseCategory
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=1000)
    conditions: list[str] = Field(default_factory=list, max_length=MAX_CONDITIONS)
    notice_period_text: str | None = Field(default=None, max_length=200)
    source_page: int = Field(gt=0)
    evidence: str = Field(min_length=1, max_length=1000)
    confidence: float

    @field_validator("confidence")
    @classmethod
    def _confidence(cls, value: float) -> float:
        return _finite_unit_interval(value)

    @field_validator("conditions")
    @classmethod
    def _non_empty_conditions(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item.strip()]


class ContractExtractionCandidate(BaseModel):
    """The full structured result requested from the contract provider on
    first pass. Empty lists are valid: absence, not fabrication."""

    parties: list[PartyCandidate] = Field(default_factory=list, max_length=MAX_PARTIES)
    obligations: list[ObligationCandidate] = Field(
        default_factory=list, max_length=MAX_OBLIGATIONS
    )
    payment_terms: list[PaymentTermCandidate] = Field(
        default_factory=list, max_length=MAX_PAYMENT_TERMS
    )
    clauses: list[ClauseCandidate] = Field(default_factory=list, max_length=MAX_CLAUSES)


class ContractRepairCandidate(BaseModel):
    """Corrected replacements for only the invalid contract items from a
    prior pass. Items may be fewer than requested, including zero, when the
    provider correctly omits an unsupported claim instead of fabricating a
    fix."""

    parties: list[PartyCandidate] = Field(default_factory=list, max_length=MAX_PARTIES)
    obligations: list[ObligationCandidate] = Field(
        default_factory=list, max_length=MAX_OBLIGATIONS
    )
    payment_terms: list[PaymentTermCandidate] = Field(
        default_factory=list, max_length=MAX_PAYMENT_TERMS
    )
    clauses: list[ClauseCandidate] = Field(default_factory=list, max_length=MAX_CLAUSES)
