"""Crash recovery and fencing for ordinary investigation starts."""
import hashlib
import time

from fastapi.testclient import TestClient

import casemind.main as main_module
from casemind.auth import owner_hash
from casemind.continuity import request_hash
from casemind.generator import demo_cases
from casemind.main import build_app
from casemind.models import digest
from casemind.store import FileStore, mutate


class CountingCloud:
    def __init__(self):
        self.load_calls = 0

    def load_case(self, snapshot, documents, execution=None):
        self.load_calls += 1


def operation_envelope(owner, case_id, key, snapshot_hash, run_id, session, bill=True):
    operation_type = "investigation:" + case_id
    operation_id = digest([owner, operation_type, key])
    parameters = {"run_id": run_id, "case_id": case_id, "session": session}
    return {
        "id": operation_id,
        "owner": owner,
        "type": operation_type,
        "request_hash": request_hash(
            owner, operation_type, key, snapshot_hash, "", [], parameters
        ),
        "snapshot_hash": snapshot_hash,
        "report_hash": "",
        "sources": [],
        "parameters": parameters,
        "bill": bill,
    }


def test_history_recovers_request_and_quota_gap_without_provider_replay(tmp_path):
    store = FileStore(tmp_path)
    cloud = CountingCloud()
    case = next(iter(demo_cases().values()))
    app = build_app(store, cloud=cloud)
    with TestClient(app) as client:
        client.get("/api/cases")
        session = client.cookies.get("casemind_session")
        snapshot = app.state.resolver.resolve(case.id)
        key = "crash-after-quota"
        run_id = hashlib.sha256(f"{session}:{case.id}:{key}".encode()).hexdigest()[:32]
        envelope = operation_envelope(
            session, case.id, key, snapshot.snapshot_id, run_id, session
        )
        prefix = f"operations/{owner_hash(session)}/{envelope['id']}"
        store.put(prefix + "/request", envelope)
        store.put(
            prefix + "/manifest",
            envelope
            | {
                "state": "reserving",
                "fence": 0,
                "created": time.time(),
                "events": [{"state": "reserving", "fence": 0}],
            },
        )
        app.state.ledger.reserve_run(session, envelope["id"])

        assert client.get("/api/history").status_code == 200
        recovered, _ = store.get(f"runs/{run_id}")
        assert recovered["status"] == "interrupted"
        assert recovered["operation_id"] == envelope["id"]
        assert store.get(prefix + "/manifest")[0]["state"] == "ready"
        assert envelope["id"] in store.get("usage/prototype-v1")[0]["runs"]

        replay = client.post(
            f"/api/cases/{case.id}/runs", json={"idempotency_key": key}
        )
        assert replay.status_code == 200
        assert replay.json()["status"] == "interrupted"
        assert cloud.load_calls == 0


def test_changed_fence_stops_before_investigation(tmp_path, monkeypatch):
    store = FileStore(tmp_path)
    case = next(iter(demo_cases().values()))
    investigation_calls = []

    class FenceChangingCloud(CountingCloud):
        def load_case(self, snapshot, documents, execution=None):
            super().load_case(snapshot, documents, execution)
            manifest = execution.operations.prefix(
                execution.owner, execution.operation_id
            ) + "/manifest"
            mutate(store, manifest, lambda value: value | {"fence": value["fence"] + 1})

    async def unexpected_investigation(*args, **kwargs):
        investigation_calls.append(True)
        raise AssertionError("stale execution reached investigation")

    cloud = FenceChangingCloud()
    monkeypatch.setattr(main_module, "investigate", unexpected_investigation)
    with TestClient(build_app(store, cloud=cloud)) as client:
        response = client.post(
            f"/api/cases/{case.id}/runs", json={"idempotency_key": "fence-change-key"}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "interrupted"
        assert cloud.load_calls == 1
        assert investigation_calls == []


def test_history_recovery_cursor_reaches_operations_after_first_page(tmp_path):
    store = FileStore(tmp_path)
    case = next(iter(demo_cases().values()))
    app = build_app(store)
    with TestClient(app) as client:
        client.get("/api/cases")
        session = client.cookies.get("casemind_session")
        snapshot = app.state.resolver.resolve(case.id)
        envelopes = []
        for index in range(130):
            key = f"cursor-operation-{index:03d}"
            envelope = operation_envelope(
                session,
                case.id,
                key,
                snapshot.snapshot_id,
                f"cursor-run-{index:03d}",
                session,
                bill=False,
            )
            store.put(
                f"operations/{owner_hash(session)}/{envelope['id']}/request", envelope
            )
            envelopes.append(envelope)
        target = max(envelopes, key=lambda value: value["id"])

        assert client.get("/api/history").status_code == 200
        assert store.get(f"runs/{target['parameters']['run_id']}")[0] is None
        cursor = store.get("recovery-cursors/" + owner_hash(session))[0]["cursor"]
        assert cursor is not None

        assert client.get("/api/history").status_code == 200
        recovered, _ = store.get(f"runs/{target['parameters']['run_id']}")
        assert recovered["status"] == "interrupted"
        assert recovered["operation_id"] == target["id"]
