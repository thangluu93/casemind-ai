from decimal import Decimal

import pytest

from casemind.analytics import compare_extracted, trace_flows
from casemind.explorers import build_document_comparison, build_money_trail, build_ownership
from casemind.generator import generate_case
from test_workspace_api import make_report


def test_money_order_exact_decimal_directions_and_roles():
    case = generate_case("circular")
    case.transactions[0].amount = Decimal("100000.000000000000000000001")
    report = make_report(case, trace_flows(case))
    view = build_money_trail(case, report)
    assert next(t for t in view["transactions"] if t["id"] == case.transactions[0].id)["amount"] == "100000.000000000000000000001"
    assert [t["timestamp"] for t in view["transactions"]] == sorted(t["timestamp"] for t in view["transactions"])
    account = case.transactions[0].sender
    incoming = build_money_trail(case, report, account_id=account, direction="incoming")
    assert all(t["receiver"] == account for t in incoming["transactions"])
    for path in view["paths"]:
        sources = {t.id: t for t in case.transactions}
        ordered = [sources[i] for i in path["ordered_transaction_ids"]]
        assert all(a.receiver == b.sender for a, b in zip(ordered, ordered[1:]))
    with pytest.raises(ValueError):
        build_money_trail(case, report, account_id="foreign")


def test_ownership_derivation_unknown_and_cycle():
    case = generate_case("ownership")
    view = build_ownership(case)
    assert {Decimal(p["effective_percentage"]) for p in view["paths"]} >= {Decimal("60"), Decimal("75")}
    case.relationships[0].percentage = None
    assert any(p["flags"]["unknown_percentage"] and p["effective_percentage"] is None
               for p in build_ownership(case)["paths"])
    with pytest.raises(ValueError):
        build_ownership(case, target_id="foreign")


def test_document_values_retain_each_page_and_anchor():
    case = generate_case("documents")
    doc = case.documents[0]
    extracted = [{"document_id": doc.id, "fields": [{"key": "Registration ID",
                  "value": "Conflicting Value", "page": 2, "confidence": 0.91,
                  "anchors": [{"start": 10, "end": 27}]}]}]
    report = make_report(case, compare_extracted(case, extracted))
    view = build_document_comparison(case, report)
    value = view["values"][0]
    assert value["raw_value"] == "Conflicting Value"
    assert value["normalized_value"] == "conflicting value"
    assert value["locator"]["page"] == 2 and value["locator"]["text_anchor"]
    assert value["locator"]["source_object"] is None
    with pytest.raises(ValueError):
        build_document_comparison(case, report, document_id="foreign")


def test_money_filters_disclose_truncation_and_do_not_combine_currencies():
    case = generate_case("circular")
    case.transactions[0].currency = "EUR"
    view = build_money_trail(case, currency="EUR", limit=1)
    assert view["coverage"]["total"] == len(case.transactions)
    assert view["coverage"]["matched"] == 1
    assert all(t["currency"] == "EUR" for t in view["transactions"])
    bounded = build_money_trail(case, limit=1)
    assert bounded["coverage"]["hidden"] == len(case.transactions) - 1


def test_ownership_cycles_never_produce_confident_product():
    case = generate_case("ownership")
    relationship = case.relationships[0]
    relationship.owner = relationship.owned
    view = build_ownership(case)
    cycle = next(p for p in view["paths"] if p["flags"]["cycle"])
    assert cycle["effective_percentage"] is None


def test_time_display_filters_are_timezone_checked_and_leave_recorded_findings_unchanged():
    case = generate_case("circular")
    report = make_report(case, trace_flows(case))
    bound = sorted(case.transactions, key=lambda tx: tx.timestamp)[1].timestamp.isoformat()
    filtered = build_money_trail(case, report, from_timestamp=bound, to_timestamp=bound)
    assert len(filtered["transactions"]) == 1
    assert filtered["filters"]["from_timestamp"] == bound
    assert filtered["paths"] == build_money_trail(case, report)["paths"]
    with pytest.raises(ValueError, match="timezone"):
        build_money_trail(case, from_timestamp="2026-09-10T08:00:00")
    with pytest.raises(ValueError, match="time window"):
        build_money_trail(case, from_timestamp="2026-09-11T08:00:00Z",
                          to_timestamp="2026-09-10T08:00:00Z")
