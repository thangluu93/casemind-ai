"""Test-only server: seed pinned deterministic evidence; never replace runtime providers.

Run from repository root. Temporary store is removed when the harness exits.
This module is not imported by the product and does not read scenario ground truth.
"""
import hashlib
import os
import tempfile
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request

from casemind.analytics import compare_extracted, entity_analysis, screening_analysis, transaction_analysis
from casemind.case_resolver import demo_snapshot, snapshot_manifest
from casemind.generator import demo_cases
from casemind.main import build_app
from casemind.models import digest
from casemind.priority import follow_up_priority
from casemind.store import FileStore


@asynccontextmanager
async def lifespan(harness):
    with tempfile.TemporaryDirectory(prefix="casemind-offline-browser-") as directory:
        store = FileStore(Path(directory))
        product = build_app(store, cloud=None)
        harness.state.store = store
        async with product.router.lifespan_context(product):
            harness.mount("/", product)
            yield


app = FastAPI(lifespan=lifespan)


@app.post("/__test__/seed")
def seed(request: Request):
    session = request.cookies.get("casemind_session", "")
    if len(session) != 64 or any(c not in "0123456789abcdef" for c in session):
        raise HTTPException(400, "First establish a real product session")
    store = request.app.state.store
    keys = {}
    for case in demo_cases().values():
        key = "offline-seeded-v1"
        run_id = hashlib.sha256(f"{session}:{case.id}:{key}".encode()).hexdigest()[:32]
        snapshot = demo_snapshot(case)
        extracted = [{"document_id": doc.id, "fields": [
            {"key": name.replace("_", " "), "value": value, "page": 1,
             "confidence": 1.0, "anchors": []} for name, value in doc.fields.items()
        ]} for doc in case.documents]
        evidence = (transaction_analysis(case) + entity_analysis(case) +
                    screening_analysis(case) + compare_extracted(case, extracted))
        report = {"run_id": run_id, "case_id": case.id, "version": 1,
                  "input_hash": snapshot.snapshot_id, "source_kind": "synthetic",
                  "model": "offline-test-fixture-no-model-call", "created_at": "2026-10-11T00:00:00+00:00",
                  "synthesis": {"summary": "Offline browser test fixture. Inspect deterministic evidence; human review is required.",
                                "hypotheses": [], "alternatives": ["Legitimate activity remains possible."],
                                "unresolved": ["External corroboration has not been performed."]},
                  "evidence": [e.model_dump(mode="json") for e in evidence], "gaps": [],
                  "usage": {"model_calls": 0, "tool_calls": 0, "input_tokens": 0, "output_tokens": 0,
                            "elapsed_seconds": 0},
                  "status": "awaiting_review", "priority": follow_up_priority(evidence)}
        report["hash"] = digest(report)
        if store.get(f"inputs/{case.id}/{snapshot.snapshot_id}")[0] is None:
            store.put(f"inputs/{case.id}/{snapshot.snapshot_id}", snapshot_manifest(snapshot))
        store.put(f"reports/{run_id}/1", report)
        store.put(f"runs/{run_id}", {"run_id": run_id, "case_id": case.id, "session": session,
                  "owner_id": session, "status": "awaiting_review", "input_hash": snapshot.snapshot_id,
                  "report_hash": report["hash"], "events": [],
                  "created_at": datetime.now(timezone.utc).isoformat()})
        keys[case.id] = {"key": key, "run_id": run_id, "report_hash": report["hash"]}
    return {"test_only": True, "cases": keys}


if __name__ == "__main__":
    # A single deterministic port; Playwright owns and terminates this process.
    uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("CASEMIND_OFFLINE_PORT", "8081")))
