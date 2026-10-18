"""Real-route integration of pinned workspaces, originals and actor authority."""
import json

from fastapi.testclient import TestClient

from casemind.analytics import entity_analysis, screening_analysis, transaction_analysis
from casemind.auth import owner_hash
from casemind.case_resolver import demo_snapshot, snapshot_manifest
from casemind.generator import demo_cases
from casemind.main import build_app
from casemind.models import digest
from casemind.store import FileStore


def seed(store, client, case, rid="route-run"):
    client.get("/api/cases")
    sid = client.cookies.get("casemind_session")
    snap = demo_snapshot(case)
    store.put(f"inputs/{case.id}/{snap.snapshot_id}", snapshot_manifest(snap))
    evidence = transaction_analysis(case) + entity_analysis(case) + screening_analysis(case)
    report = {"run_id": rid, "case_id": case.id, "version": 1, "input_hash": snap.snapshot_id,
              "source_kind": "synthetic", "evidence": [e.model_dump(mode="json") for e in evidence],
              "gaps": [], "synthesis": {"summary": "Synthetic tool observations for review.",
                  "hypotheses": [], "alternatives": ["Legitimate activity may explain indicators."],
                  "unresolved": []}, "status": "awaiting_review", "model": "offline-test-only",
              "usage": {"tool_calls": 0, "input_tokens": 0, "output_tokens": 0, "elapsed_seconds": 0}}
    report["hash"] = digest(report)
    store.put(f"reports/{rid}/1", report)
    store.put(f"runs/{rid}", {"run_id": rid, "case_id": case.id, "session": sid,
                             "status": "awaiting_review", "input_hash": snap.snapshot_id, "events": []})
    return sid, report


def test_workspace_originals_exports_and_scoped_questions(tmp_path):
    store = FileStore(tmp_path)
    case = next(iter(demo_cases().values()))
    with TestClient(build_app(store)) as client:
        sid, report = seed(store, client, case)
        before = store.get("reports/route-run/1")[0]
        for route in ("workspace", "money-trail", "ownership", "documents"):
            response = client.get(f"/api/runs/route-run/{route}")
            assert response.status_code == 200, response.text
        reason = client.get(f"/api/runs/route-run/transactions/{case.transactions[0].id}/reasons")
        assert reason.status_code == 200
        pdf = client.get(f"/api/runs/route-run/documents/{case.documents[0].id}.pdf")
        assert pdf.status_code == 200
        assert pdf.content.startswith(b"%PDF-")
        assert "attachment" in pdf.headers["content-disposition"]
        assert "sandbox" in pdf.headers["content-security-policy"]
        for fmt in ("html", "pdf"):
            exported = client.get(f"/api/runs/route-run/exports/report.{fmt}")
            assert exported.status_code == 200, exported.text[:400]
            assert report["hash"].encode() in exported.content
        question = {"question": "How many transactions are in this case?",
                    "expected_report_hash": report["hash"], "idempotency_key": "question-key"}
        answer = client.post("/api/runs/route-run/questions", json=question)
        assert answer.status_code == 200, answer.text
        assert answer.json()["facts"][0]["transaction_count"] == len(case.transactions)
        assert client.post("/api/runs/route-run/questions", json=question).json() == answer.json()
        assert client.post("/api/runs/route-run/questions", json=question | {
            "question": "How many other transactions?"}).status_code == 409
        assert store.get("usage/prototype-v1")[0] is None  # Deterministic answer is non-billable.
        assert client.get("/api/history").json()["items"][0]["run_id"] == "route-run"
        assert store.get("reports/route-run/1")[0] == before
    with TestClient(build_app(store)) as stranger:
        assert stranger.get("/api/runs/route-run/workspace").status_code == 404
        assert stranger.get("/api/history").json()["items"] == []
    with TestClient(build_app(FileStore(tmp_path))) as restarted:
        restarted.cookies.set("casemind_session", sid)
        assert restarted.get("/api/runs/route-run/report").json() == report


def test_authenticated_structured_follow_up_keeps_parent_immutable(tmp_path, monkeypatch):
    monkeypatch.setenv("CASEMIND_SESSION_SECRET", "s" * 40)
    monkeypatch.setenv("CASEMIND_GOOGLE_CLIENT_ID", "test-client")
    monkeypatch.setenv("CASEMIND_INVESTIGATOR_SUBJECTS", "test-investigator")
    store = FileStore(tmp_path)
    app = build_app(store)
    case = next(iter(demo_cases().values()))
    with TestClient(app) as client:
        old_session, report = seed(store, client, case)
        # Exercise authority using a verified-session issuance; no forged OAuth runtime fallback.
        token = app.state.sessions.issue("test-investigator", old_session)
        client.cookies.set("casemind_auth", token)
        assert client.get("/api/auth/session").json()["authenticated"]
        create = {"notes": "Collect a new synthetic transfer", "requested_checks": ["transaction"],
                  "report_hash": report["hash"], "expected_version": 1,
                  "idempotency_key": "follow-up-key"}
        response = client.post("/api/runs/route-run/follow-ups", json=create)
        assert response.status_code == 200, response.text
        task = response.json()
        record = {"id": "new-transfer", "sender": case.accounts[0].id,
                  "receiver": case.accounts[1].id, "amount": "123.45", "currency": "USD",
                  "timestamp": "2026-10-11T01:00:00+00:00"}
        batch = {"version": 1, "classification": "synthetic", "records": [
                 {"group": "transactions", "action": "add", "record": record}]}
        stage = client.post(f"/api/follow-ups/{task['id']}/intake", content=json.dumps(batch),
                  headers={"content-type": "application/json"}, params={"expected_version": task["version"],
                  "idempotency_key": "stage-key", "filename": "synthetic.json"})
        assert stage.status_code == 200, stage.text
        staged_response = stage.json()
        replay_stage = client.post(f"/api/follow-ups/{task['id']}/intake", content=json.dumps(batch),
                  headers={"content-type": "application/json"}, params={"expected_version": task["version"],
                  "idempotency_key": "stage-key", "filename": "synthetic.json"})
        assert replay_stage.status_code == 200, replay_stage.text
        assert replay_stage.json() == staged_response
        changed = client.post(f"/api/follow-ups/{task['id']}/intake", content=json.dumps(batch | {"records": []}),
                  headers={"content-type": "application/json"}, params={"expected_version": task["version"],
                  "idempotency_key": "stage-key", "filename": "synthetic.json"})
        assert changed.status_code == 409
        task = staged_response
        commit = {"batch": {"version": 1, "classification": "synthetic", "records": []},
                  "expected_version": task["version"], "idempotency_key": "commit-key"}
        result = client.post(f"/api/follow-ups/{task['id']}/commit", json=commit)
        assert result.status_code == 200, result.text
        assert client.post(f"/api/follow-ups/{task['id']}/commit", json=commit).json() == result.json()
        child = result.json()["child_case_id"]
        detail = client.get(f"/api/cases/{child}")
        assert detail.status_code == 200, detail.text
        assert len(detail.json()["transactions"]) == len(case.transactions) + 1
        assert client.get(f"/api/cases/{child}/workspace").status_code == 200
        assert client.get("/api/runs/route-run/report").json() == report
        assert client.get(f"/api/cases/{case.id}").status_code == 200
        assert client.post("/api/auth/sign-out", json={}).status_code == 200
        client.cookies.set("casemind_auth", token)
        assert client.get("/api/auth/session").status_code == 401
    with TestClient(build_app(store)) as copied:
        copied.cookies.set("casemind_session", old_session)
        assert copied.get("/api/runs/route-run/report").status_code == 404
        assert copied.get(f"/api/cases/{child}").status_code == 404
    assert store.get(f"claimed-sessions/{owner_hash(old_session)}")[0]["revoked"]


def test_structured_batch_permutation_has_same_child_identity(tmp_path, monkeypatch):
    monkeypatch.setenv("CASEMIND_SESSION_SECRET", "s" * 40)
    monkeypatch.setenv("CASEMIND_GOOGLE_CLIENT_ID", "test-client")
    monkeypatch.setenv("CASEMIND_INVESTIGATOR_SUBJECTS", "test-investigator")
    store, case = FileStore(tmp_path), next(iter(demo_cases().values()))
    app = build_app(store)
    with TestClient(app) as client:
        sid, report = seed(store, client, case)
        client.cookies.set("casemind_auth", app.state.sessions.issue("test-investigator", sid))
        records = [{"group": "entities", "action": "add", "record": {
            "id": "synthetic-" + name, "name": "Synthetic " + name, "kind": "company"}}
            for name in ("Alpha", "Beta")]
        results = []
        for index, items in enumerate((records, list(reversed(records)))):
            task = client.post("/api/runs/route-run/follow-ups", json={
                "notes": "Collect fictional entities", "requested_checks": [],
                "report_hash": report["hash"], "expected_version": 1,
                "idempotency_key": "permutation-" + str(index)}).json()
            committed = client.post(f"/api/follow-ups/{task['id']}/commit", json={
                "expected_version": task["version"], "idempotency_key": "commit-permutation",
                "batch": {"version": 1, "classification": "synthetic", "records": items}})
            assert committed.status_code == 200, committed.text
            results.append(committed.json())
        assert results[0]["child_case_id"] == results[1]["child_case_id"]
        assert results[0]["child_snapshot_id"] == results[1]["child_snapshot_id"]


def test_actual_pdf_original_and_fifty_page_limits(tmp_path):
    import asyncio
    from io import BytesIO
    from reportlab.pdfgen.canvas import Canvas
    from casemind.intake import stage_stream
    from casemind.source_catalog import SourceCatalog
    import pytest

    def pdf(pages):
        output = BytesIO()
        canvas = Canvas(output, pagesize=(40, 40))
        for i in range(pages):
            canvas.drawString(1, 20, "Synthetic page " + str(i))
            canvas.showPage()
        canvas.save()
        return output.getvalue()

    async def chunks(data):
        for start in range(0, len(data), 1024):
            yield data[start:start + 1024]
    store = FileStore(tmp_path)
    original = pdf(50)
    staged = asyncio.run(stage_stream(chunks(original), store, "owner", "pdf-task", "application/pdf"))
    assert staged["verified_page_count"] == 50
    data, _ = store.get_blob(staged["key"], staged["generation"])
    assert data == original
    reference = SourceCatalog(store).put(data, "application/pdf")
    assert SourceCatalog(store).read(reference) == original
    with pytest.raises(ValueError):
        asyncio.run(stage_stream(chunks(pdf(51)), store, "owner", "too-many", "application/pdf"))
    counters = {"bytes": 0, "pdfs": 0, "pages": 0}
    for i in range(10):
        asyncio.run(stage_stream(chunks(pdf(5)), store, "owner", "multi-task", "application/pdf", counters,
                                idempotency_key="part-" + str(i), expected_version=i))
    assert counters["pages"] == 50 and counters["pdfs"] == 10
    with pytest.raises(ValueError):
        asyncio.run(stage_stream(chunks(pdf(1)), store, "owner", "multi-task", "application/pdf", counters))
