from app.demo.fixtures import DEMOS, validate_fixtures
from app.schemas.document import DemoQuestionResponse


def test_three_synthetic_demo_fixtures_validate_with_unique_types() -> None:
    validate_fixtures()
    assert len(DEMOS) == 3
    assert {demo.document_type for demo in DEMOS} == {
        "contract",
        "technical_specification",
        "generic",
    }
    assert all("fictional" in demo.filename for demo in DEMOS)


def test_demo_answers_keep_page_evidence_and_insufficient_has_no_citations() -> None:
    for demo in DEMOS:
        for raw in demo.questions:
            question = DemoQuestionResponse.model_validate(raw)
            if question.status == "insufficient_evidence":
                assert question.citations == []
            for citation in question.citations:
                assert citation.evidence in demo.pages[citation.page - 1]
