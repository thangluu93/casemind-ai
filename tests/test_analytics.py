from datetime import timedelta
from decimal import Decimal

import pytest

from casemind.analytics import (
    compare_extracted,
    detect_structuring,
    entity_analysis,
    screening_analysis,
    trace_flows,
    transaction_analysis,
)
from casemind.generator import generate_case


def test_temporal_paths_cycles_structuring_and_negative_controls():
    layering = generate_case("layering")
    findings = transaction_analysis(layering)
    assert {e.tool for e in findings} >= {"trace_flows", "detect_structuring"}
    structuring = next(e for e in findings if e.tool == "detect_structuring")
    assert structuring.payload["total"] == "19200"
    assert not detect_structuring(generate_case("layering", control=True))
    circular = generate_case("circular")
    cycles = [e for e in trace_flows(circular) if e.tool == "detect_cycles"]
    assert len(cycles) == 1
    assert cycles[0].payload["hours"] == 4
    assert cycles[0].payload["accounts"][0] == cycles[0].payload["accounts"][-1]
    assert not trace_flows(generate_case("circular", control=True))


def test_changed_amount_currency_and_direction_change_findings():
    case = generate_case("circular")
    changed = case.model_copy(deep=True)
    changed.transactions[-1].amount = Decimal("100")
    assert not any(e.tool == "detect_cycles" for e in trace_flows(changed))
    changed = case.model_copy(deep=True)
    changed.transactions[-2].amount = Decimal("100")
    assert not any(e.tool == "detect_cycles" for e in trace_flows(changed))
    changed = case.model_copy(deep=True)
    changed.transactions[-1].currency = "EUR"
    assert not any(e.tool == "detect_cycles" for e in trace_flows(changed))
    changed = case.model_copy(deep=True)
    changed.transactions[-1].sender, changed.transactions[-1].receiver = (
        changed.transactions[-1].receiver,
        changed.transactions[-1].sender,
    )
    assert not any(e.tool == "detect_cycles" for e in trace_flows(changed))
    changed = case.model_copy(deep=True)
    changed.transactions[-1].timestamp -= timedelta(days=3)
    assert not any(e.tool == "detect_cycles" for e in trace_flows(changed))


def test_ownership_decimal_arithmetic_missing_percentages_and_cycles():
    case = generate_case("ownership")
    findings = entity_analysis(case)
    percentages = {e.payload.get("effective_percentage") for e in findings}
    assert {"60", "75"} <= percentages
    discrepancy = next(e for e in findings if e.tool == "compare_ownership_declaration")
    assert discrepancy.payload["effective_percentage"] == "60"
    assert discrepancy.payload["declared_owner_name"] != discrepancy.payload["candidate_name"]
    assert all(
        e.payload.get("effective_percentage") is None
        for e in entity_analysis(generate_case("ownership", control=True))
        if e.tool == "trace_ownership"
    )
    case.relationships[1].owner = case.entities[0].id
    assert any(
        e.payload.get("status") == "unresolved_cycle_or_depth" for e in entity_analysis(case)
    )


def test_watchlist_name_collisions_do_not_clear_or_merge_entities():
    case = generate_case("screening")
    findings = screening_analysis(case)
    assert {e.payload["status"] for e in findings} == {"likely_false_positive", "potential_match"}
    findings = screening_analysis(generate_case("screening", control=True))
    assert {e.payload["status"] for e in findings} == {"likely_false_positive", "inconclusive"}
    assert len(case.entities) == 5


def extracted_fixture(case, confidence=0.9):
    # Unit fixture models the Document AI boundary, not a fallback in production.
    return [
        {
            "document_id": d.id,
            "fields": [
                {
                    "key": k,
                    "value": v,
                    "page": 1,
                    "confidence": confidence,
                    "anchors": {"value": [{"start": 10, "end": 20}]},
                }
                for k, v in d.fields.items()
            ],
        }
        for d in case.documents
    ]


def test_anchored_document_mismatch_and_low_confidence_are_distinct():
    case = generate_case("documents")
    findings = compare_extracted(case, extracted_fixture(case))
    assert {e.payload.get("status") for e in findings} >= {
        "declared_field_mismatch",
        "cross_document_mismatch",
    }
    assert not any(
        e.claim_kind == "indicator" for e in compare_extracted(case, extracted_fixture(case, 0.2))
    )
    control = generate_case("documents", control=True)
    assert not any(
        e.claim_kind == "indicator" for e in compare_extracted(control, extracted_fixture(control))
    )
    with pytest.raises(KeyError):
        compare_extracted(case, [{"document_id": "other-case", "fields": []}])


def test_large_path_search_is_bounded_and_reports_truncation():
    case = generate_case("layering")
    sources = case.transactions[-7:-4]
    for index in range(50):
        for original in sources:
            tx = original.model_copy(update={"id": f"added-{index}-{original.id}"})
            case.transactions.append(tx)
    findings = trace_flows(case)
    assert len(findings) <= 41
    assert findings[-1].payload.get("truncated") is True
