from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from casemind.generator import demo_cases
from casemind.main import build_app
from casemind.store import Conflict, FileStore, UsageLedger


def test_cas_and_concurrent_global_allowance(tmp_path):
    store = FileStore(tmp_path)
    assert store.put("reports/r/1", {"hash": "first"}) == 1
    with pytest.raises(Conflict):
        store.put("reports/r/1", {"hash": "changed"})
    ledger = UsageLedger(store, max_runs=3, session_runs=10)

    def reserve(index):
        try:
            ledger.reserve_run("s", str(index))
            return True
        except ValueError:
            return False

    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(pool.map(reserve, range(10))) == 3
    reservations = store.get("usage/prototype-v1")[0]
    for run_id in reservations["runs"]:
        ledger.reserve_run("s", run_id)  # Every successful concurrent reservation replays.
    assert store.get("usage/prototype-v1")[0] == reservations
    assert len(store.get("usage/prototype-v1")[0]["runs"]) == 3


def test_scoped_sources_live_only_and_cross_site_write_rejection(tmp_path):
    with TestClient(build_app(FileStore(tmp_path))) as client:
        cases = client.get("/api/cases").json()
        first, second = list(demo_cases().values())[:2]
        assert len(cases) == 6
        assert [c["kind"] for c in cases].count("safety_control") == 1
        assert (
            client.get(f"/api/cases/{first.id}/sources/{second.entities[0].id}").status_code == 404
        )
        assert (
            client.post(
                f"/api/cases/{first.id}/runs", json={"idempotency_key": "abcdefgh"}
            ).status_code
            == 503
        )
        assert (
            client.post(
                f"/api/cases/{first.id}/runs",
                json={"idempotency_key": "abcdefgh"},
                headers={"Origin": "https://evil.example"},
            ).status_code
            == 403
        )


def test_immutable_review_scope_hash_and_restart(tmp_path):
    store = FileStore(tmp_path)
    app = build_app(store)
    case = next(iter(demo_cases().values()))
    with TestClient(app) as client:
        client.get("/api/cases")
        session = client.cookies.get("casemind_session")
        store.put("runs/r", {"session": session, "case_id": case.id, "status": "awaiting_review"})
        store.put("reports/r/1", {"version": 1, "hash": "a" * 64})
        body = {
            "report_hash": "a" * 64,
            "expected_version": 1,
            "action": "approved",
            "reason": "Reviewed source evidence",
        }
        assert (
            client.post("/api/runs/r/review", json=body | {"report_hash": "b" * 64}).status_code
            == 409
        )
        assert client.post("/api/runs/r/review", json=body).status_code == 200
        assert (
            client.post("/api/runs/r/review", json=body | {"action": "rejected"}).status_code == 409
        )
    with TestClient(build_app(FileStore(tmp_path))) as restarted:
        restarted.cookies.set("casemind_session", session)
        assert restarted.get("/api/runs/r/review").json()["action"] == "approved"
    with TestClient(build_app(FileStore(tmp_path))) as stranger:
        assert stranger.get("/api/runs/r/report").status_code == 404
