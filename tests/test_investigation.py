import pytest
from google.adk.models.llm_request import LlmRequest
from google.genai import types

from casemind.analytics import transaction_analysis
from casemind.generator import generate_case
from casemind.investigation import InvestigationPlan, RunBudget, validate_synthesis
from casemind.models import ReportClaim, Synthesis


def test_fabricated_citations_are_rejected():
    findings = transaction_analysis(generate_case("layering"))
    report = Synthesis(
        summary="For investigator review",
        hypotheses=[ReportClaim(text="Possible layering", evidence_ids=[findings[0].id])],
        alternatives=["Settlement"],
        unresolved=["Account purpose"],
    )
    assert validate_synthesis(report, findings) == report
    report.hypotheses[0].evidence_ids = ["ev-invented"]
    with pytest.raises(ValueError):
        validate_synthesis(report, findings)


def test_model_schema_serialization_and_hard_call_bound():
    budget = RunBudget()
    request = LlmRequest(
        contents=[types.Content(role="user", parts=[types.Part(text="hello")])],
        config=types.GenerateContentConfig(
            max_output_tokens=100, response_schema=InvestigationPlan
        ),
    )
    for _ in range(12):
        budget.before_model(None, request)
    with pytest.raises(ValueError):
        budget.before_model(None, request)
    budget = RunBudget()
    request.contents[0].parts[0].text = "x" * 50001
    with pytest.raises(ValueError):
        budget.before_model(None, request)
