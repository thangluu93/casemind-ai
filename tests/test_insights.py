"""Deterministic insights, embedded-instruction control and bounded advisory validation."""
import asyncio
from decimal import Decimal

import pytest

from casemind.advisory import context_for, run_advisory, validate
from casemind.analytics import (WITHHELD, compare_extracted, entity_analysis, redact_untrusted,
                                screening_analysis, transaction_analysis)
from casemind.case_resolver import demo_snapshot
from casemind.continuity import Operations
from casemind.generator import demo_cases, generate_case
from casemind.insights import (GraphQuery, ThresholdSimulation, alternative_checks,
                               change_drivers, run_graph_query, simulate_thresholds, typology_map)
from casemind.models import digest
from casemind.priority import follow_up_priority
from casemind.store import FileStore, UsageLedger


def extracted(case):
    return [{"document_id": d.id, "fields": [{"key": k, "value": v, "page": 1, "confidence": 1.0,
                                              "anchors": []} for k, v in d.fields.items()]}
            for d in case.documents]


def report_for(case, gaps=()):
    evidence = (transaction_analysis(case) + entity_analysis(case) + screening_analysis(case)
                + compare_extracted(case, extracted(case)))
    report = {"run_id": "run", "case_id": case.id, "version": 1,
              "input_hash": demo_snapshot(case).snapshot_id,
              "evidence": [e.model_dump(mode="json") for e in evidence], "gaps": list(gaps),
              "synthesis": {"summary": "Review required.", "hypotheses": [], "alternatives": [],
                            "unresolved": []}}
    report["hash"] = digest(report)
    return report


def test_embedded_instructions_are_detected_and_withheld_from_model_context():
    case = generate_case("injection")
    findings = compare_extracted(case, extracted(case))
    flagged = [e for e in findings if e.tool == "detect_embedded_instructions"]
    assert len(flagged) == 1 and flagged[0].claim_kind == "indicator"
    assert set(flagged[0].payload["patterns"]) >= {"override_instructions", "disposition_command"}
    model_view = str(redact_untrusted([e.model_dump(mode="json") for e in findings]))
    assert "Ignore previous" not in model_view and "approve the case" not in model_view
    assert WITHHELD in model_view
    assert follow_up_priority(findings)["level"] == "follow_up"
    control = generate_case("injection", control=True)
    assert not [e for e in compare_extracted(control, extracted(control))
                if e.tool == "detect_embedded_instructions"]


def test_redaction_is_a_no_op_for_the_five_scenarios():
    for case in demo_cases().values():
        if case.title.endswith("safety control"):
            continue
        evidence = report_for(case)["evidence"]
        assert redact_untrusted(evidence) == evidence


def test_typologies_distinguish_observed_and_not_evaluated():
    case = generate_case("layering")
    view = typology_map(case, report_for(case))
    states = {t["id"]: t["state"] for t in view["typologies"]}
    assert states["rapid_pass_through"] == "observed" and states["structuring"] == "observed"
    assert states["sanctions_pep_exposure"] == "evaluated_not_observed"
    gapped = typology_map(case, report_for(case, [{"role": "compliance"}]))
    assert {t["id"]: t["state"] for t in gapped["typologies"]}["sanctions_pep_exposure"] == "not_evaluated"


def test_what_if_defaults_match_record_and_overrides_change_flags():
    case = generate_case("layering")
    report = report_for(case)
    baseline = simulate_thresholds(case, report, ThresholdSimulation())
    assert not baseline["changed"] and baseline["persisted"] is False
    raised = simulate_thresholds(case, report, ThresholdSimulation(structuring_threshold="4000"))
    structuring = next(t for t in raised["tools"] if t["tool"] == "detect_structuring")
    assert structuring["removed"] and not structuring["simulated_flagged"]
    with pytest.raises(ValueError):
        ThresholdSimulation(structuring_threshold=4000.0)


def test_change_drivers_rank_unknown_ownership_and_alternative_checks():
    case = generate_case("ownership", control=True)
    drivers = change_drivers(case, report_for(case))["drivers"]
    assert any(d["request_type"] == "ownership_register" for d in drivers)
    assert [d["impact_score"] for d in drivers] == sorted((d["impact_score"] for d in drivers), reverse=True)
    layering = generate_case("layering")
    checks = alternative_checks(layering, report_for(layering))["checks"]
    assert {c["status"] for c in checks} <= {"supports_alternative", "does_not_support", "not_evaluable"}
    assert any(c["evidence_id"] for c in checks if "settlement" in c["alternative"])


def test_graph_query_is_bounded_and_scoped():
    case = generate_case("circular")
    result = run_graph_query(case, GraphQuery(start_id=case.entities[0].id, max_hops=3,
                                              min_amount="10000"))
    assert result["paths"] and all(p["hops"] <= 3 for p in result["paths"])
    assert all(Decimal(a) >= 10000 for p in result["paths"] for a in p["amounts"])
    with pytest.raises(ValueError):
        run_graph_query(case, GraphQuery(start_id="foreign:account"))
    with pytest.raises(ValueError):
        GraphQuery(start_id=case.accounts[0].id, max_hops=9)


def test_advisory_validation_rejects_digits_foreign_citations_and_unknown_ids():
    case = generate_case("layering")
    snapshot, report = demo_snapshot(case), report_for(case)
    known = report["evidence"][1]["id"]
    good = {"points": [{"evidence_ids": [known], "legitimate_explanation": "A settlement run.",
                        "what_would_falsify": "Invoices for each transfer."}],
            "overall_caution": "Hypotheses only.", "abstained": False}
    assert validate("challenge", good, snapshot, report, {})["status"] == "advisory_requires_review"
    with pytest.raises(ValueError):
        validate("challenge", good | {"overall_caution": "Two of 3 transfers."}, snapshot, report, {})
    with pytest.raises(ValueError):
        validate("challenge", good | {"points": [good["points"][0] | {"evidence_ids": ["ev-x"]}]},
                 snapshot, report, {})
    plan = {"start_id": case.accounts[0].id, "end_id": None, "max_hops": 3, "currency": None,
            "min_amount": None, "window_hours": None, "rationale": "Follow outgoing transfers.",
            "abstained": False}
    assert validate("graph_query_plan", plan, snapshot, report, {})["query"]["max_hops"] == 3
    with pytest.raises(ValueError):
        validate("graph_query_plan", plan | {"start_id": "invented"}, snapshot, report, {})
    context = context_for("rfi", snapshot, report, "")
    draft = {"recipient_role": "customer", "subject": "Supporting documents", "body": "Please share.",
             "requested_items": ["Invoices"], "evidence_ids": [known],
             "driver_ids": [context["change_drivers"][0]["id"]]}
    assert validate("rfi", {"drafts": [draft], "abstained": False}, snapshot, report,
                    context)["status"] == "draft_not_sent"
    with pytest.raises(ValueError):
        validate("rfi", {"drafts": [draft | {"driver_ids": ["cd-invented"]}], "abstained": False},
                 snapshot, report, context)


def test_advisory_operation_is_idempotent_and_context_is_redacted(tmp_path):
    store = FileStore(tmp_path)
    operations = Operations(store, UsageLedger(store))
    case = generate_case("injection")
    snapshot, report = demo_snapshot(case), report_for(case)
    seen = []

    async def generate(kind, context, execution):
        seen.append(str(context))
        return {"points": [], "overall_caution": "Insufficient indicators.", "abstained": True}

    def call():
        return asyncio.run(run_advisory(operations, "owner", "run", snapshot, report, "challenge",
                                        "advisory-key", report["hash"], generate))
    first = call()
    assert first["result"]["abstained"] and call() == first and len(seen) == 1
    assert "approve the case" not in seen[0]
