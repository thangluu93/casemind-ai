import time

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from casemind.analytics import transaction_analysis
from casemind.generator import demo_cases, generate_case
from casemind.main import build_app
from casemind.models import ReviewRequest, StartRun
from casemind.models import digest
from casemind.priority import follow_up_priority
from casemind.store import FileStore


def test_priority_is_deterministic_and_does_not_count_duplicate_indicators():
    findings = transaction_analysis(generate_case("layering"))
    priority = follow_up_priority(findings)
    assert priority["score"] == 30
    assert follow_up_priority(findings + findings)["score"] == 30
    assert "not a probability" in priority["interpretation"]
    assert (
        follow_up_priority(transaction_analysis(generate_case("layering", control=True)))["score"]
        == 0
    )


def test_arbitrary_upload_scope_and_blank_review_reasons_are_rejected():
    with pytest.raises(ValidationError):
        StartRun(idempotency_key="abcdefgh", documents=["https://outside.example/instructions"])
    with pytest.raises(ValidationError):
        ReviewRequest(report_hash="a" * 64, expected_version=1, action="approved", reason="     ")


def test_abandoned_run_reconciles_after_restart_without_new_provider_calls(tmp_path):
    store = FileStore(tmp_path)
    case = next(iter(demo_cases().values()))
    with TestClient(build_app(store)) as client:
        client.get("/api/cases")
        session = client.cookies.get("casemind_session")
        store.put(
            "runs/abandoned",
            {
                "session": session,
                "case_id": case.id,
                "status": "running",
                "started_epoch": time.time() - 200,
                "events": [{"role": "transaction", "status": "tool_completed"}],
            },
        )
        value = client.get("/api/runs/abandoned").json()
        assert value["status"] == "interrupted"
        assert "session" not in value
        assert len(value["events"]) == 1
        assert store.get("usage/prototype-v1")[0] is None


def test_report_sources_remain_pinned_when_the_current_case_changes(tmp_path, monkeypatch):
    from casemind.main import CASES

    frozen = generate_case("ownership")
    original_name = frozen.entities[0].identifiers["beneficial_owner"]
    changed = frozen.model_copy(deep=True)
    changed.entities[0].identifiers["beneficial_owner"] = "Changed after the report"
    monkeypatch.setitem(CASES, frozen.id, changed)
    store = FileStore(tmp_path)
    input_hash = digest(frozen)
    store.put(
        f"inputs/{frozen.id}/{input_hash}",
        {"hash": input_hash, "case": frozen.model_dump(mode="json")},
    )
    with TestClient(build_app(store)) as client:
        client.get("/api/cases")
        session = client.cookies.get("casemind_session")
        store.put(
            "runs/pinned",
            {
                "session": session,
                "case_id": frozen.id,
                "status": "awaiting_review",
                "input_hash": input_hash,
            },
        )
        path = f"/api/runs/pinned/sources/{frozen.entities[0].id}"
        assert client.get(path).json()["identifiers"]["beneficial_owner"] == original_name
        assert (
            client.get(f"/api/cases/{frozen.id}/sources/{frozen.entities[0].id}").json()[
                "identifiers"
            ]["beneficial_owner"]
            != original_name
        )
        assert (
            client.get("/api/runs/pinned/case").json()["entities"][0]["identifiers"][
                "beneficial_owner"
            ]
            == original_name
        )
        assert (
            client.get(
                f"/api/runs/pinned/sources/{generate_case('screening').entities[0].id}"
            ).status_code
            == 404
        )


def test_gcs_object_rate_limit_is_retried_under_the_same_precondition():
    from google.api_core.exceptions import TooManyRequests

    from casemind.store import GCSStore

    class Blob:
        generation, calls = 7, []

        def upload_from_string(self, data, **kwargs):
            self.calls.append(kwargs["if_generation_match"])
            if len(self.calls) < 3:
                raise TooManyRequests("object mutation rate")

    blob = Blob()
    store = GCSStore(type("Client", (), {"bucket": lambda self, name: type(
        "Bucket", (), {"blob": lambda self, key: blob})()})(), "bucket")
    assert store.put("runs/x", {"a": 1}, 5, backoff=(0, 0, 0)) == 7
    assert blob.calls == [5, 5, 5]
    blob.calls.clear()
    Blob.upload_from_string = lambda self, data, **kwargs: (_ for _ in ()).throw(TooManyRequests("x"))
    try:
        store.put("runs/x", {}, 5, backoff=(0,))
    except TooManyRequests:
        pass
    else:
        raise AssertionError("Exhausted rate-limit retries must surface")
