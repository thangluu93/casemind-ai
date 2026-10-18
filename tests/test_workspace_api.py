import pytest

from casemind.analytics import screening_analysis
from casemind.generator import generate_case
from casemind.models import digest
from casemind.workspace import build_workspace, validate_screening_assessment


def make_report(case, evidence):
    report = {"case_id": case.id, "run_id": "run-test", "input_hash": digest(case),
              "version": 1, "evidence": [e.model_dump(mode="json") for e in evidence],
              "synthesis": {"summary": "Review supplied evidence", "hypotheses": []}, "gaps": []}
    report["hash"] = digest(report)
    return report


def test_preview_does_not_imply_run_or_clearance_and_caps_inventory():
    case = generate_case("screening")
    view = build_workspace(case, limit=1)
    assert view.scope.run_id is None and view.findings == []
    assert view.coverage["state"] == "not_evaluated"
    assert len(view.sources) == 1 and view.hidden_counts["sources"] > 0
    assert all(c["evidence_id"] is None for c in view.screening_candidates)
    empty = case.model_copy(deep=True)
    empty.watchlist = []
    assert build_workspace(empty).coverage["screening_state"] == "not_supplied"


def test_assessment_pins_candidates_hash_and_version_without_mutating_report():
    case = generate_case("screening")
    report = make_report(case, screening_analysis(case))
    candidate = build_workspace(case, report).screening_candidates[0]
    before = digest(report)
    request = {"candidate_ids": [candidate["id"]], "report_hash": report["hash"],
               "expected_version": 1, "assessment": "inconclusive",
               "reason": "Conflicting identifiers require review", "idempotency_key": "test-key-123"}
    assert validate_screening_assessment(case, report, request)["candidate_ids"] == [candidate["id"]]
    assert digest(report) == before
    with pytest.raises(ValueError):
        validate_screening_assessment(case, report, {**request, "candidate_ids": ["foreign"]})
    with pytest.raises(ValueError):
        validate_screening_assessment(case, report, {**request, "expected_version": 2})


def test_unknown_tool_has_raw_fallback_and_foreign_snapshot_fails():
    case = generate_case("screening")
    findings = screening_analysis(case)
    findings[0].tool_version = 999
    report = make_report(case, findings)
    assert build_workspace(case, report).findings[0].renderer == "raw"
    with pytest.raises(ValueError):
        build_workspace(case, {**report, "input_hash": "foreign"})
    with pytest.raises(ValueError):
        build_workspace(case, limit=501)


def test_supplemental_lineage_rejects_foreign_ids():
    case = generate_case("screening")
    findings = screening_analysis(case)
    findings[0].ordered_transaction_ids = ["tx-foreign"]
    with pytest.raises(ValueError, match="foreign transactions"):
        build_workspace(case, make_report(case, findings))


def test_v2_manifest_identity_is_used_instead_of_case_digest():
    from casemind.case_resolver import create_manifest, snapshot_from_manifest
    case = generate_case("screening")
    snap = snapshot_from_manifest(create_manifest(case, {}, {}, owner_id="test-owner"))
    report = make_report(case, screening_analysis(case))
    report["input_hash"] = snap.snapshot_id
    report["hash"] = digest({k: v for k, v in report.items() if k != "hash"})
    view = build_workspace(case, report, snap)
    assert view.scope.input_hash == snap.snapshot_id
    assert view.scope.input_hash != digest(case)


def test_uploaded_structured_source_preserves_nested_object_and_locator():
    from casemind.case_resolver import create_manifest, snapshot_from_manifest
    case = generate_case("screening")
    source_id = case.entities[0].id
    obj = {"sha256": "b" * 64, "media_type": "text/csv", "byte_size": 128,
           "generation": 3, "storage_key": "sources/input-csv"}
    metadata = {source_id: {"origin": "uploaded", "classification": "synthetic",
                           "source_object": obj, "locator": "row/2"}}
    snapshot = snapshot_from_manifest(create_manifest(case, {}, metadata))
    record = next(r for r in build_workspace(case, snapshot=snapshot).sources if r["id"] == source_id)
    assert record["origin"] == "uploaded"
    assert record["source_object"] == obj
    assert record["locator"] == "row/2"
