"""Explicit idempotent seed command for the three synthetic precomputed demos."""

import asyncio
import sys

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import get_sessionmaker
from app.demo.fixtures import DEMOS, FIXTURE_VERSION, stable_id, validate_fixtures
from app.models.document import (
    AnalysisFinding,
    AnalysisImportantDate,
    AnalysisRisk,
    AnalysisRiskEvidence,
    ContractClause,
    ContractPaymentTerm,
    Document,
    DocumentAnalysis,
    DocumentClassification,
    DocumentPage,
    DocumentSection,
    TechnicalConstraint,
    TechnicalRequirement,
)


class DemoSeedError(Exception):
    pass


def _analysis(demo) -> DocumentAnalysis:  # type: ignore[no-untyped-def]
    analysis_id = stable_id(f"{demo.slug}:analysis")
    analysis = DocumentAnalysis(
        id=analysis_id,
        document_type=demo.document_type,
        extractor={
            "contract": "contract_terms",
            "technical_specification": "technical_specification_requirements",
            "generic": "generic",
        }[demo.document_type],
        status="completed",
        summary_title=demo.title,
        summary_purpose="Demonstrate a precomputed evidence-backed analysis.",
        summary_text=demo.description,
        summary_key_topics=[section[0] for section in demo.sections],
        provider="precomputed",
        model=FIXTURE_VERSION,
        retry_count=0,
        latency_ms=None,
        input_tokens=None,
        output_tokens=None,
        findings=[
            AnalysisFinding(
                id=stable_id(f"{demo.slug}:finding:{index}"),
                ordinal=index,
                title=title,
                description=description,
                category="demo",
                importance="high",
                source_page=page,
                evidence=evidence,
                confidence=1.0,
            )
            for index, (title, description, page, evidence) in enumerate(
                demo.findings, 1
            )
        ],
        important_dates=[
            AnalysisImportantDate(
                id=stable_id(f"{demo.slug}:date:{index}"),
                ordinal=index,
                label=label,
                raw_value=raw,
                normalized_date=None,
                source_page=page,
                evidence=evidence,
                confidence=1.0,
            )
            for index, (label, raw, page, evidence) in enumerate(
                demo.important_dates, 1
            )
        ],
        risks=[
            AnalysisRisk(
                id=stable_id(f"{demo.slug}:risk:{index}"),
                ordinal=index,
                title=title,
                description=description,
                category="demo",
                severity="medium",
                confidence=1.0,
                evidence=[
                    AnalysisRiskEvidence(
                        id=stable_id(f"{demo.slug}:risk-evidence:{index}"),
                        ordinal=1,
                        page=page,
                        text=evidence,
                    )
                ],
            )
            for index, (title, description, page, evidence) in enumerate(demo.risks, 1)
        ],
    )
    if demo.document_type == "contract":
        analysis.contract_payment_terms = [
            ContractPaymentTerm(
                id=stable_id(f"{demo.slug}:payment"),
                ordinal=1,
                payer="Lumen Orchard Cooperative",
                payee="Blue Finch Systems",
                amount_text="1,200 fictional credits",
                schedule_text="first business day of each month",
                source_page=2,
                evidence="Customer shall pay Provider 1,200 fictional credits on the first business day of each month",
                confidence=1.0,
            )
        ]
        analysis.contract_clauses = [
            ContractClause(
                id=stable_id(f"{demo.slug}:renewal"),
                ordinal=1,
                category="renewal",
                title="Renewal",
                description="Renews for one-year terms unless notice is given.",
                conditions=[],
                notice_period_text="45 days",
                source_page=3,
                evidence="The agreement renews for one-year terms unless either party gives 45 days written notice",
                confidence=1.0,
            ),
            ContractClause(
                id=stable_id(f"{demo.slug}:termination"),
                ordinal=2,
                category="termination",
                title="Termination",
                description="Termination for material breach follows a cure period.",
                conditions=["material breach"],
                notice_period_text="15-day cure period",
                source_page=3,
                evidence="Either party may terminate for material breach after a 15-day cure period",
                confidence=1.0,
            ),
        ]
    elif demo.document_type == "technical_specification":
        analysis.technical_requirements = [
            TechnicalRequirement(
                id=stable_id(f"{demo.slug}:fr"),
                ordinal=1,
                category="functional",
                identifier="FR-1",
                statement="Register a sensor within 30 seconds.",
                priority="must",
                actor="service",
                measurable_criterion="within 30 seconds",
                source_page=1,
                evidence="FR-1: The service shall register a sensor within 30 seconds",
                confidence=1.0,
            ),
            TechnicalRequirement(
                id=stable_id(f"{demo.slug}:sec"),
                ordinal=2,
                category="security",
                identifier="SEC-1",
                statement="Encrypt stored readings using AES-256.",
                priority="must",
                actor="service",
                measurable_criterion="AES-256",
                source_page=2,
                evidence="SEC-1: The service shall encrypt stored readings using AES-256",
                confidence=1.0,
            ),
            TechnicalRequirement(
                id=stable_id(f"{demo.slug}:int"),
                ordinal=3,
                category="integration",
                identifier="INT-1",
                statement="Expose a JSON API over HTTPS.",
                priority="must",
                actor="service",
                measurable_criterion="JSON over HTTPS",
                source_page=2,
                evidence="INT-1: The service shall expose a JSON API over HTTPS",
                confidence=1.0,
            ),
        ]
        analysis.technical_constraints = [
            TechnicalConstraint(
                id=stable_id(f"{demo.slug}:constraint"),
                ordinal=1,
                category="deployment",
                statement="Run in a private network.",
                value_text="private network",
                source_page=3,
                evidence="The service must run in a private network",
                confidence=1.0,
            )
        ]
    return analysis


def _document(demo) -> Document:  # type: ignore[no-untyped-def]
    document_id = stable_id(f"{demo.slug}:document")
    section_ids = [
        stable_id(f"{demo.slug}:section:{i}") for i in range(1, len(demo.sections) + 1)
    ]
    return Document(
        id=document_id,
        filename=demo.filename,
        content_hash=demo.content_hash,
        page_count=len(demo.pages),
        status="parsed",
        demo_slug=demo.slug,
        demo_version=FIXTURE_VERSION,
        demo_title=demo.title,
        demo_description=demo.description,
        demo_document_type=demo.document_type,
        demo_questions=list(demo.questions),
        pages=[
            DocumentPage(page_number=i, text=text)
            for i, text in enumerate(demo.pages, 1)
        ],
        sections=[
            DocumentSection(
                id=section_ids[i - 1],
                ordinal=i,
                title=title,
                level=1,
                parent_section_id=None,
                page_start=start,
                page_end=end,
                section_path=[title],
                text="\n".join(demo.pages[start - 1 : end]),
            )
            for i, (title, start, end) in enumerate(demo.sections, 1)
        ],
        classification=DocumentClassification(
            id=stable_id(f"{demo.slug}:classification"),
            document_type=demo.document_type,
            confidence=1.0,
            reason="Precomputed synthetic demo classification.",
            evidence=[{"page": 1, "text": demo.pages[0].splitlines()[-1]}],
            provider="precomputed",
            model=FIXTURE_VERSION,
            status="completed",
            latency_ms=None,
            input_tokens=None,
            output_tokens=None,
        ),
        analysis=_analysis(demo),
    )


async def seed_demos() -> tuple[int, int]:
    validate_fixtures()
    async with get_sessionmaker()() as session:
        existing = list(
            (
                await session.execute(
                    select(Document)
                    .where(Document.demo_slug.is_not(None))
                    .options(
                        selectinload(Document.pages),
                        selectinload(Document.sections),
                        selectinload(Document.classification),
                        selectinload(Document.analysis),
                    )
                )
            ).scalars()
        )
        if existing:
            if len(existing) != len(DEMOS):
                raise DemoSeedError("partial demo seed state detected; no changes made")
            expected = {demo.slug: demo for demo in DEMOS}
            for row in existing:
                fixture = expected.get(row.demo_slug or "")
                if (
                    fixture is None
                    or row.demo_version != FIXTURE_VERSION
                    or row.content_hash != fixture.content_hash
                    or [page.text for page in row.pages] != list(fixture.pages)
                    or len(row.sections) != len(fixture.sections)
                    or row.classification is None
                    or row.classification.provider != "precomputed"
                    or row.classification.model != FIXTURE_VERSION
                    or row.classification.document_type != fixture.document_type
                    or row.analysis is None
                    or row.analysis.provider != "precomputed"
                    or row.analysis.model != FIXTURE_VERSION
                    or row.analysis.document_type != fixture.document_type
                ):
                    raise DemoSeedError(
                        "demo fixture/version/content mismatch; no changes made"
                    )
            return 0, len(existing)
        session.add_all([_document(demo) for demo in DEMOS])
        await session.commit()
        return len(DEMOS), 0


async def _main() -> int:
    try:
        created, reused = await seed_demos()
    except Exception as exc:  # noqa: BLE001 - CLI boundary must fail safely
        print(f"Demo seed failed: {type(exc).__name__}", file=sys.stderr)
        return 1
    print(
        f"Demo seed complete: created={created} reused={reused} slugs={','.join(d.slug for d in DEMOS)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
