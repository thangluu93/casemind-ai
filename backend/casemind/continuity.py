"""Owner-scoped operation authority; projections never authorize provider replay."""
import time
from dataclasses import dataclass

from .auth import owner_hash
from .models import digest
from .store import Conflict, mutate


def request_hash(owner, operation_type, key, snapshot_hash, report_hash, sources, parameters):
    return digest({"owner": owner, "type": operation_type, "key": key,
                   "snapshot": snapshot_hash, "report": report_hash,
                   "sources": sorted(set(sources)), "parameters": parameters})


@dataclass
class ExecutionContext:
    operations: object
    owner: str
    operation_id: str
    fence: int
    deadline: float

    def check(self):
        value, _ = self.operations.get(self.owner, self.operation_id)
        if (not value or time.time() >= self.deadline or value["state"] != "executing"
                or value["fence"] != self.fence or value["owner"] != self.owner):
            raise Conflict("Execution lease expired or superseded")
        return max(0.001, self.deadline - time.time())


class Operations:
    def __init__(self, store, ledger):
        self.store, self.ledger = store, ledger

    def prefix(self, owner, operation_id):
        return f"operations/{owner_hash(owner)}/{operation_id}"

    def get(self, owner, operation_id):
        return self.store.get(self.prefix(owner, operation_id) + "/manifest")

    def reserve(self, owner, operation_type, key, snapshot_hash, report_hash, sources, parameters, bill=True):
        if not key or len(key) > 100:
            raise ValueError("A bounded idempotency key is required")
        operation_id = digest([owner, operation_type, key])
        prefix = self.prefix(owner, operation_id)
        canonical = request_hash(owner, operation_type, key, snapshot_hash,
                                 report_hash, sources, parameters)
        envelope = {"id": operation_id, "owner": owner, "type": operation_type,
                    "request_hash": canonical, "snapshot_hash": snapshot_hash,
                    "report_hash": report_hash, "sources": sorted(set(sources)),
                    "parameters": parameters, "bill": bill}
        try:
            self.store.put(prefix + "/request", envelope)
        except Conflict:
            existing, _ = self.store.get(prefix + "/request")
            if existing["request_hash"] != canonical:
                raise Conflict("Idempotency key reused with a different request")
        value = mutate(self.store, prefix + "/manifest", lambda old: old or envelope | {
            "state": "reserving", "fence": 0, "created": time.time(),
            "events": [{"state": "reserving", "fence": 0}],
        })
        if value["state"] == "reserving":
            self._project(value)
            value = mutate(self.store, prefix + "/manifest", lambda old:
                           self._transition(old, "ready") if old["state"] == "reserving" else old)
        self._events(value)
        return value

    def _events(self, value):
        prefix = self.prefix(value["owner"], value["id"])
        for index, event in enumerate(value.get("events", [])):
            key = f"{prefix}/events/{index:06d}"
            try:
                self.store.put(key, event)
            except Conflict:
                if self.store.get(key)[0] != event:
                    raise Conflict("Immutable operation event conflict")

    def _transition(self, value, state, **updates):
        event = {"state": state, "at": time.time(), "fence": updates.get("fence", value["fence"])}
        return value | updates | {"state": state, "events": [*value.get("events", []), event]}

    def _project(self, value):
        if value.get("bill", True):
            self.ledger.reserve_run(value["owner"], value["id"])
        mutate(self.store, f"history/{owner_hash(value['owner'])}/{value['id']}",
               lambda old: old or {"operation_id": value["id"], "type": value["type"],
                                   "created": value["created"]})

    def begin(self, owner, operation_id):
        prefix = self.prefix(owner, operation_id)
        def acquire(old):
            if old is None or old["state"] != "ready":
                raise Conflict("Operation cannot be executed again")
            return self._transition(old, "executing", fence=old["fence"] + 1,
                                    deadline=time.time() + 120)
        value = mutate(self.store, prefix + "/manifest", acquire)
        self._events(value)
        return ExecutionContext(self, owner, operation_id, value["fence"], value["deadline"])

    def finish(self, context, result=None, error=None):
        context.check()
        def terminal(old):
            if old["fence"] != context.fence or old["state"] != "executing":
                raise Conflict("Stale operation terminal write")
            if time.time() >= old["deadline"]:
                raise Conflict("Execution deadline expired")
            return self._transition(old, "terminal", result=result, error=error,
                                    completed=time.time())
        value = mutate(self.store, self.prefix(context.owner, context.operation_id) + "/manifest",
                      terminal)
        self._events(value)
        return value

    def recover(self, owner, cursor=None, limit=100):
        keys, next_cursor = self.store.scan_keys(f"operations/{owner_hash(owner)}/",
                                                 cursor=cursor, limit=limit)
        recovered = []
        for key in keys:
            if not key.endswith("/request"):
                continue
            request, _ = self.store.get(key)
            prefix = key.removesuffix("/request")
            value = mutate(self.store, prefix + "/manifest", lambda old: old or request | {
                "state": "reserving", "fence": 0, "created": time.time(),
                "events": [{"state": "reserving", "fence": 0}],
            })
            self._project(value)
            def reconcile(old):
                if old["state"] == "reserving":
                    return self._transition(old, "ready")
                if old["state"] == "executing" and old["deadline"] <= time.time():
                    return self._transition(old, "terminal", error="interrupted", result=None)
                return old
            value = mutate(self.store, prefix + "/manifest", reconcile)
            self._events(value)
            recovered.append(value)
        return recovered, next_cursor

    def history(self, owner, cursor=None, limit=100):
        keys, cursor = self.store.scan_keys(f"history/{owner_hash(owner)}/", cursor=cursor,
                                            limit=limit)
        return {"scope": "complete_for_actor", "items": [self.store.get(k)[0] for k in keys],
                "cursor": cursor}


class FollowUps:
    def __init__(self, store):
        self.store = store

    def replay(self, owner, follow_up_id, key, expected_version, request):
        """Check before work; normalized request excludes generated result fields."""
        prefix = f"follow-ups/{owner_hash(owner)}/{follow_up_id}"
        canonical = digest({"request": request, "expected_version": expected_version})
        envelope_key = prefix + "/requests/" + digest(key)
        if not key or len(key) > 100:
            raise ValueError("A bounded idempotency key is required")
        envelope = {"hash": canonical, "request": request, "expected_version": expected_version}
        try:
            self.store.put(envelope_key, envelope)
        except Conflict:
            prior, _ = self.store.get(envelope_key)
            if prior["hash"] != canonical:
                raise Conflict("Follow-up request key conflict")
        current, _ = self.store.get(prefix + "/manifest")
        applied = (current or {}).get("commands", {}).get(digest(key))
        return applied["result"] if applied else None

    def prepare(self, owner, follow_up_id, key, expected_version, request):
        replay = self.replay(owner, follow_up_id, key, expected_version, request)
        if replay is not None:
            return replay
        prefix = f"follow-ups/{owner_hash(owner)}/{follow_up_id}"
        canonical = digest({"request": request, "expected_version": expected_version})
        def acquire(current):
            if current is None or current.get("version", 0) != expected_version:
                raise Conflict("Follow-up version changed")
            pending = current.get("pending_command")
            if pending and (pending["key"] != key or pending["hash"] != canonical):
                raise Conflict("Another follow-up command is prepared; retry its original request")
            return current | {"pending_command": {"key": key, "hash": canonical,
                                                   "expected_version": expected_version}}
        return mutate(self.store, prefix + "/manifest", acquire)

    def abandon(self, owner, follow_up_id, key, expected_version):
        """Explicit cancel releases preparation without replaying or rolling back side effects."""
        prefix = f"follow-ups/{owner_hash(owner)}/{follow_up_id}"
        def release(current):
            if current is None or current.get("version", 0) != expected_version:
                raise Conflict("Follow-up version changed")
            pending = current.get("pending_command")
            if not pending or pending["key"] != key:
                raise Conflict("Prepared command does not match")
            return current | {"pending_command": None}
        return mutate(self.store, prefix + "/manifest", release)

    def find(self, owners, follow_up_id):
        for owner in owners:
            value, generation = self.store.get(f"follow-ups/{owner_hash(owner)}/{follow_up_id}/manifest")
            if value and value.get("owner") == owner:
                return value, generation
        raise KeyError(follow_up_id)

    def command(self, owner, follow_up_id, key, expected_version, command):
        prefix = f"follow-ups/{owner_hash(owner)}/{follow_up_id}"
        if any(field in command for field in ("id", "owner", "events", "commands", "version", "pending_command")):
            raise ValueError("Command cannot replace authority fields")
        current, _ = self.store.get(prefix + "/manifest")
        for field in ("run_id", "report_hash", "parent_snapshot", "source_evidence", "source_question"):
            if current and field in command and field in current and current[field] != command[field]:
                raise Conflict("Follow-up parent binding is immutable")
        canonical = digest({"command": command, "expected_version": expected_version})
        request_key = prefix + "/commands/" + digest(key)
        envelope = {"hash": canonical, "command": command, "expected_version": expected_version}
        try:
            self.store.put(request_key, envelope)
        except Conflict:
            prior, _ = self.store.get(request_key)
            if prior["hash"] != canonical:
                raise Conflict("Follow-up command key conflict")
        if any(field in command for field in ("id", "owner", "events", "commands", "version", "pending_command")):
            raise ValueError("Command cannot replace authority fields")
        def apply(current):
            prior = (current or {}).get("commands", {}).get(digest(key))
            if prior:
                if prior["hash"] != canonical:
                    raise Conflict("Follow-up command key conflict")
                return current
            pending = (current or {}).get("pending_command")
            if pending and pending["key"] != key:
                raise Conflict("Another follow-up command is prepared")
            for field in ("run_id", "report_hash", "parent_snapshot", "source_evidence", "source_question"):
                if current and field in command and field in current and current[field] != command[field]:
                    raise Conflict("Follow-up parent binding is immutable")
            if (current or {}).get("version", 0) != expected_version:
                raise Conflict("Follow-up version changed")
            result = (current or {"id": follow_up_id, "owner": owner, "events": []}) | command
            result["version"] = expected_version + 1
            result["pending_command"] = None
            result["events"] = [*(current or {}).get("events", []),
                                {"key": key, "command": command, "at": time.time()}]
            response = {k: v for k, v in result.items() if k != "commands"}
            result["commands"] = (current or {}).get("commands", {}) | {
                digest(key): {"hash": canonical, "result": response}}
            return result
        result = mutate(self.store, prefix + "/manifest", apply)
        return result["commands"][digest(key)]["result"]



def semantic_diff(before, after):
    """Compare stable record IDs rather than stored list positions."""
    left, right = before.sources, after.sources
    return {"added": sorted(right.keys() - left.keys()), "removed": sorted(left.keys() - right.keys()),
            "changed": sorted(key for key in left.keys() & right.keys()
                              if digest(left[key]) != digest(right[key]))}


def index_run(store, owner, run_id):
    """Durable owner-prefix projection; a guessed run ID grants no authority."""
    run, _ = store.get(f"runs/{run_id}")
    if not run:
        raise KeyError(run_id)
    value = {"run_id": run_id, "case_id": run["case_id"], "owner": owner}
    mutate(store, f"owner-runs/{owner_hash(owner)}/{run_id}", lambda old: old or value)
    mutate(store, f"history/{owner_hash(owner)}/run-{run_id}", lambda old: old or value | {"type": "run"})
    return value


def run_history(store, owner, cursor=None, limit=100):
    keys, cursor = store.scan_keys(f"owner-runs/{owner_hash(owner)}/", cursor=cursor, limit=limit)
    runs = []
    for key in keys:
        projection, _ = store.get(key)
        if not projection or projection.get("owner") != owner:
            continue
        run, _ = store.get(f"runs/{projection['run_id']}")
        if run:
            runs.append(run | {"run_id": projection["run_id"]})
    return {"scope": "complete_for_actor", "items": runs, "next_cursor": cursor}
