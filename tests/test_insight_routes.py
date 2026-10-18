"""Real-route checks for insights, maker-checker review, triage and bilingual export."""
from fastapi.testclient import TestClient

from casemind.main import build_app
from casemind.store import FileStore
from casemind.generator import demo_cases
from test_workspace_routes import seed


def test_insight_routes_are_pinned_and_do_not_change_the_report(tmp_path):
    store = FileStore(tmp_path)
    case = next(iter(demo_cases().values()))
    with TestClient(build_app(store)) as client:
        _, report = seed(store, client, case)
        before = store.get("reports/route-run/1")
        for route in ("typologies", "change-drivers", "alternative-checks"):
            response = client.get(f"/api/runs/route-run/{route}")
            assert response.status_code == 200, response.text
        what_if = client.post("/api/runs/route-run/what-if", json={"structuring_threshold": "4000"})
        assert what_if.status_code == 200 and what_if.json()["persisted"] is False
        assert client.post("/api/runs/route-run/what-if", json={"structuring_threshold": 1.5}).status_code == 422
        query = client.post("/api/runs/route-run/graph-query",
                            json={"start_id": case.accounts[0].id, "max_hops": 2})
        assert query.status_code == 200 and query.json()["paths"]
        assert client.post("/api/runs/route-run/graph-query", json={"start_id": "x"}).status_code == 422
        # No configured cloud: the advisory fails explicitly instead of returning a canned answer.
        advisory = client.post("/api/runs/route-run/advisories/challenge", json={
            "idempotency_key": "advisory-route", "expected_report_hash": report["hash"]})
        assert advisory.status_code == 422
        listed = client.get("/api/runs/route-run/advisories").json()["items"]
        assert listed[0]["state"] == "terminal" and "error" in listed[0]
        vi = client.get("/api/runs/route-run/exports/report.html?lang=vi")
        assert vi.status_code == 200 and 'lang="vi"' in vi.text and report["hash"] in vi.text
        assert client.get("/api/runs/route-run/exports/report.pdf?lang=vi").status_code == 422
        assert store.get("reports/route-run/1") == before
        evaluation = client.get("/api/evaluation").json()
        assert evaluation["latest"]
        for summary in evaluation["latest"].values():
            assert not {"expected", "predicted", "case_id", "expected_labels"} & summary.keys()


def test_maker_checker_requires_a_distinct_signed_in_investigator(tmp_path, monkeypatch):
    monkeypatch.setenv("CASEMIND_SESSION_SECRET", "s" * 40)
    monkeypatch.setenv("CASEMIND_GOOGLE_CLIENT_ID", "test-client")
    monkeypatch.setenv("CASEMIND_INVESTIGATOR_SUBJECTS", "maker,checker")
    store = FileStore(tmp_path)
    app = build_app(store)
    case = next(iter(demo_cases().values()))
    with TestClient(app) as client:
        old_session, report = seed(store, client, case)
        assert client.post("/api/runs/route-run/checks").status_code == 409
        review = client.post("/api/runs/route-run/review", json={
            "report_hash": report["hash"], "expected_version": 1, "action": "needs_follow_up",
            "reason": "Request supporting invoices."})
        assert review.status_code == 200, review.text
        client.cookies.set("casemind_auth", app.state.sessions.issue("maker", old_session))
        check = client.post("/api/runs/route-run/checks").json()
        decision = {"report_hash": report["hash"], "decision": "dispute",
                    "reason": "Ownership gap needs escalation."}
        assert client.post(f"/api/checks/{check['id']}/decision", json=decision).status_code == 403
    with TestClient(app) as checker:
        assert checker.get(f"/api/checks/{check['id']}").status_code == 403
        checker.cookies.set("casemind_auth", app.state.sessions.issue("checker"))
        detail = checker.get(f"/api/checks/{check['id']}")
        assert detail.status_code == 200 and detail.json()["report_view"]["report_hash"] == report["hash"]
        result = checker.post(f"/api/checks/{check['id']}/decision", json=decision)
        assert result.status_code == 200 and result.json()["outcome"] == "escalated_disagreement"
        assert checker.post(f"/api/checks/{check['id']}/decision", json=decision).status_code == 409
        assert store.get("reviews/route-run/1")[0]["action"] == "needs_follow_up"


def test_triage_ranks_investigated_cases_first(tmp_path):
    store = FileStore(tmp_path)
    case = next(iter(demo_cases().values()))
    with TestClient(build_app(store)) as client:
        seed(store, client, case)
        items = client.get("/api/triage").json()["items"]
        assert items[0]["case_id"] == case.id and items[0]["state"] == "investigated"
        assert items[0]["score"] is not None
        assert {i["state"] for i in items[1:]} == {"not_investigated"}
