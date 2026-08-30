"""Original synthetic demo sources and deterministic provenance validation."""

import hashlib
import uuid
from dataclasses import dataclass
from typing import Literal

from app.schemas.document import DemoQuestionResponse

NAMESPACE = uuid.UUID("21ba0a4d-44c8-42d9-87ef-a66e95caad3a")
FIXTURE_VERSION = "demo-v1"


def stable_id(value: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, value)


@dataclass(frozen=True)
class DemoFixture:
    slug: str
    filename: str
    title: str
    description: str
    document_type: Literal["contract", "technical_specification", "generic"]
    pages: tuple[str, ...]
    sections: tuple[tuple[str, int, int], ...]
    findings: tuple[tuple[str, str, int, str], ...]
    important_dates: tuple[tuple[str, str, int, str], ...]
    risks: tuple[tuple[str, str, int, str], ...]
    questions: tuple[dict[str, object], ...]

    @property
    def content_hash(self) -> str:
        return hashlib.sha256("\n\f\n".join(self.pages).encode()).hexdigest()


def _question(
    slug: str,
    key: str,
    question: str,
    answer: str,
    page: int | None,
    evidence: str | None,
) -> dict[str, object]:
    citations = (
        []
        if page is None
        else [
            {
                "chunk_id": str(stable_id(f"{slug}:{key}:chunk")),
                "page": page,
                "evidence": evidence,
            }
        ]
    )
    return {
        "id": key,
        "question": question,
        "status": "insufficient_evidence" if page is None else "answered",
        "answer": answer,
        "citations": citations,
    }


DEMOS = (
    DemoFixture(
        slug="sample-contract",
        filename="fictional-services-agreement.txt",
        title="Fictional services agreement",
        description="A synthetic contract demonstrating payment, renewal, and termination evidence.",
        document_type="contract",
        pages=(
            "FICTIONAL DEMO — NOT LEGAL ADVICE\n1. Parties\nThis agreement is between Lumen Orchard Cooperative (Customer) and Blue Finch Systems (Provider).",
            "2. Fees\nCustomer shall pay Provider 1,200 fictional credits on the first business day of each month.",
            "3. Term and Termination\nThe agreement renews for one-year terms unless either party gives 45 days written notice. Either party may terminate for material breach after a 15-day cure period.",
        ),
        sections=(
            ("1. Parties", 1, 1),
            ("2. Fees", 2, 2),
            ("3. Term and Termination", 3, 3),
        ),
        findings=(
            (
                "Monthly payment",
                "Customer pays 1,200 fictional credits monthly.",
                2,
                "Customer shall pay Provider 1,200 fictional credits on the first business day of each month",
            ),
        ),
        important_dates=(),
        risks=(
            (
                "Automatic renewal",
                "Notice is required to avoid renewal.",
                3,
                "renews for one-year terms unless either party gives 45 days written notice",
            ),
        ),
        questions=(
            _question(
                "sample-contract",
                "renewal",
                "How much notice prevents renewal?",
                "Either party must give 45 days written notice.",
                3,
                "The agreement renews for one-year terms unless either party gives 45 days written notice",
            ),
            _question(
                "sample-contract",
                "payment",
                "When is payment due?",
                "Payment is due on the first business day of each month.",
                2,
                "Customer shall pay Provider 1,200 fictional credits on the first business day of each month",
            ),
            _question(
                "sample-contract",
                "insurance",
                "What insurance is required?",
                "The document does not provide enough information to answer this confidently.",
                None,
                None,
            ),
        ),
    ),
    DemoFixture(
        slug="sample-technical-specification",
        filename="fictional-sensor-specification.txt",
        title="Fictional sensor platform specification",
        description="A synthetic specification with functional, security, integration, and deployment constraints.",
        document_type="technical_specification",
        pages=(
            "FICTIONAL DEMO\n1. Functional Requirements\nFR-1: The service shall register a sensor within 30 seconds.",
            "2. Security and Integration\nSEC-1: The service shall encrypt stored readings using AES-256. INT-1: The service shall expose a JSON API over HTTPS.",
            "3. Constraints\nThe service must run in a private network and support 500 concurrent sensors.",
        ),
        sections=(
            ("1. Functional Requirements", 1, 1),
            ("2. Security and Integration", 2, 2),
            ("3. Constraints", 3, 3),
        ),
        findings=(
            (
                "Sensor registration",
                "Registration completes within 30 seconds.",
                1,
                "The service shall register a sensor within 30 seconds",
            ),
        ),
        important_dates=(),
        risks=(
            (
                "Capacity ceiling",
                "The stated concurrent-sensor capacity is bounded.",
                3,
                "support 500 concurrent sensors",
            ),
        ),
        questions=(
            _question(
                "sample-technical-specification",
                "encryption",
                "How are readings protected at rest?",
                "Stored readings use AES-256 encryption.",
                2,
                "The service shall encrypt stored readings using AES-256",
            ),
            _question(
                "sample-technical-specification",
                "capacity",
                "How many concurrent sensors are supported?",
                "The service supports 500 concurrent sensors.",
                3,
                "support 500 concurrent sensors",
            ),
            _question(
                "sample-technical-specification",
                "retention",
                "How long are readings retained?",
                "The document does not provide enough information to answer this confidently.",
                None,
                None,
            ),
        ),
    ),
    DemoFixture(
        slug="sample-generic-report",
        filename="fictional-garden-program-report.txt",
        title="Fictional garden program report",
        description="A synthetic report demonstrating findings, dates, risks, and decisions.",
        document_type="generic",
        pages=(
            "FICTIONAL DEMO\nExecutive Summary\nThe pilot installed 24 community garden beds and served 80 households.",
            "Schedule and Decision\nThe steering group approved expansion on March 15, 2027. Phase two begins June 1, 2027.",
            "Risks\nSummer water access remains unresolved and may delay the expansion.",
        ),
        sections=(
            ("Executive Summary", 1, 1),
            ("Schedule and Decision", 2, 2),
            ("Risks", 3, 3),
        ),
        findings=(
            (
                "Expansion approved",
                "The steering group approved phase-two expansion.",
                2,
                "The steering group approved expansion on March 15, 2027",
            ),
        ),
        important_dates=(
            ("Phase two begins", "June 1, 2027", 2, "Phase two begins June 1, 2027"),
        ),
        risks=(
            (
                "Water access",
                "Unresolved water access may delay expansion.",
                3,
                "Summer water access remains unresolved and may delay the expansion",
            ),
        ),
        questions=(
            _question(
                "sample-generic-report",
                "households",
                "How many households did the pilot serve?",
                "The pilot served 80 households.",
                1,
                "The pilot installed 24 community garden beds and served 80 households",
            ),
            _question(
                "sample-generic-report",
                "start",
                "When does phase two begin?",
                "Phase two begins June 1, 2027.",
                2,
                "Phase two begins June 1, 2027",
            ),
            _question(
                "sample-generic-report",
                "budget",
                "What is the expansion budget?",
                "The document does not provide enough information to answer this confidently.",
                None,
                None,
            ),
        ),
    ),
)


def validate_fixtures() -> None:
    if (
        len(DEMOS) != 3
        or len({d.slug for d in DEMOS}) != 3
        or len({d.document_type for d in DEMOS}) != 3
    ):
        raise ValueError(
            "demo fixtures must contain exactly three unique slugs and types"
        )
    for demo in DEMOS:
        if len(demo.pages) < 3:
            raise ValueError(f"{demo.slug}: expected at least three pages")
        page_numbers = set(range(1, len(demo.pages) + 1))
        for _, _, page, evidence in (
            *demo.findings,
            *demo.important_dates,
            *demo.risks,
        ):
            if page not in page_numbers or evidence not in demo.pages[page - 1]:
                raise ValueError(f"{demo.slug}: analysis evidence mismatch")
        for raw in demo.questions:
            question = DemoQuestionResponse.model_validate(raw)
            if question.status == "insufficient_evidence" and question.citations:
                raise ValueError(f"{demo.slug}: insufficient answer has citations")
            for citation in question.citations:
                if (
                    citation.page not in page_numbers
                    or citation.evidence not in demo.pages[citation.page - 1]
                ):
                    raise ValueError(f"{demo.slug}: question citation mismatch")
