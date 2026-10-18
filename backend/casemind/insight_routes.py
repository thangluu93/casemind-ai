"""Routes for deterministic insights, bounded advisories, maker-checker review and triage."""
import json
from datetime import datetime, timezone
from importlib import resources

from fastapi import HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from .advisory import INSTRUCTIONS, SCHEMAS, bounded_generate, run_advisory
from .auth import owner_hash
from .case_resolver import snapshot_from_manifest
from .exports import build_export_view
from .insights import (GraphQuery, ThresholdSimulation, alternative_checks, change_drivers,
                       run_graph_query, simulate_thresholds, typology_map)
from .investigation import SAFETY
from .models import Evidence, digest
from .priority import follow_up_priority
from .store import Conflict


class CheckDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    report_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    decision: str = Field(pattern=r"^(concur|dispute)$")
    reason: str = Field(min_length=5, max_length=2000)

    @field_validator("reason")
    @classmethod
    def meaningful(cls, value):
        value = value.strip()
        if len(value) < 5:
            raise ValueError("A meaningful checker reason is required")
        return value


def register_insight_routes(app, cases, pinned, owned_run):
    def require_report(run_id, request):
        owned_run(request, run_id)
        value, _ = app.state.store.get(f"reports/{run_id}/1")
        if not value:
            raise HTTPException(409, "A completed pinned report is required")
        return value

    def pinned_with_report(run_id, request):
        report = require_report(run_id, request)
        return pinned(request, run_id), report

    def owner_scopes(request):
        if request.state.authenticated:
            owners, cursor = app.state.sessions.owner_scopes(request.state.owner)
            if cursor:
                raise HTTPException(409, "Ownership bootstrap exceeds this page; retry after history completes")
            return owners
        return [request.state.owner]

    @app.get("/api/evaluation")
    def evaluation():
        try:
            text = resources.files("casemind").joinpath("data/evaluation-summary.json").read_text()
        except FileNotFoundError as exc:
            raise HTTPException(404, "No evaluation summary is packaged with this build") from exc
        return json.loads(text)

    @app.get("/api/runs/{run_id}/typologies")
    def typologies(run_id: str, request: Request):
        snap, report = pinned_with_report(run_id, request)
        return typology_map(snap.case, report)

    @app.get("/api/runs/{run_id}/change-drivers")
    def drivers(run_id: str, request: Request):
        snap, report = pinned_with_report(run_id, request)
        return change_drivers(snap.case, report)

    @app.get("/api/runs/{run_id}/alternative-checks")
    def alternatives(run_id: str, request: Request):
        snap, report = pinned_with_report(run_id, request)
        return alternative_checks(snap.case, report)

    @app.post("/api/runs/{run_id}/what-if")
    def what_if(run_id: str, body: dict, request: Request):
        snap, report = pinned_with_report(run_id, request)
        try:
            overrides = ThresholdSimulation.model_validate(body)
        except ValidationError as exc:
            raise HTTPException(422, "Invalid simulation parameters: " + str(exc)[:300]) from exc
        return simulate_thresholds(snap.case, report, overrides)

    @app.post("/api/runs/{run_id}/graph-query")
    def graph_query(run_id: str, body: dict, request: Request):
        snap = pinned(request, run_id)
        try:
            query = GraphQuery.model_validate(body)
        except ValidationError as exc:
            raise HTTPException(422, "Invalid graph query: " + str(exc)[:300]) from exc
        return run_graph_query(snap.case, query)

    async def generate(kind, context, execution):
        if not app.state.cloud:
            raise ValueError("Live Google synthesis is not configured")
        return await bounded_generate(
            app.state.store, execution, context, SAFETY + "\n" + INSTRUCTIONS[kind],
            SCHEMAS[kind], f"advisory-usage/{owner_hash(execution.owner)}/{execution.operation_id}")

    @app.post("/api/runs/{run_id}/advisories/{kind}")
    async def advisory(run_id: str, kind: str, body: dict, request: Request):
        snap, report = pinned_with_report(run_id, request)
        value = await run_advisory(app.state.operations, request.state.owner, run_id, snap, report,
                                   kind, body.get("idempotency_key", ""),
                                   body.get("expected_report_hash"), generate,
                                   body.get("question", ""))
        return (value.get("result") or {"error": value.get("error", "Advisory pending")}) | {
            "id": value["id"], "kind": kind, "state": value["state"]}

    @app.get("/api/runs/{run_id}/advisories")
    def advisories(run_id: str, request: Request):
        owned_run(request, run_id)
        items, cursor = [], None
        for owner in owner_scopes(request):
            keys, cursor = app.state.store.scan_keys(f"operations/{owner_hash(owner)}/", limit=500)
            for key in keys:
                if not key.endswith("/manifest"):
                    continue
                value, _ = app.state.store.get(key)
                if value["type"].startswith("advisory:") and value["parameters"].get("run_id") == run_id:
                    items.append((value.get("result") or {"error": value.get("error", "Pending")})
                                 | {"id": value["id"], "kind": value["parameters"]["kind"],
                                    "state": value["state"],
                                    "question": value["parameters"].get("question", "")})
        return {"items": items, "next_cursor": cursor}

    # Maker-checker: the maker's immutable review stays authoritative; a second investigator
    # records concurrence or dispute against the same report hash.
    @app.post("/api/runs/{run_id}/checks")
    def request_check(run_id: str, request: Request):
        run, _ = owned_run(request, run_id)
        report = require_report(run_id, request)
        review, _ = app.state.store.get(f"reviews/{run_id}/1")
        if not review or review.get("report_hash") != report["hash"]:
            raise HTTPException(409, "Record the maker review before requesting a second check")
        check_id = digest([run_id, report["hash"]])[:32]
        value = {"id": check_id, "run_id": run_id, "case_id": run["case_id"],
                 "report_hash": report["hash"], "maker": owner_hash(request.state.owner),
                 "maker_review_hash": digest(review), "maker_action": review["action"],
                 "at": datetime.now(timezone.utc).isoformat()}
        existing, _ = app.state.store.get(f"checks/{check_id}/request")
        if existing:
            return existing | {"decision": app.state.store.get(f"checks/{check_id}/decision")[0]}
        try:
            app.state.store.put(f"checks/{check_id}/request", value)
        except Conflict:
            value = app.state.store.get(f"checks/{check_id}/request")[0]
        return value | {"decision": None}

    @app.get("/api/runs/{run_id}/checks")
    def run_checks(run_id: str, request: Request):
        report = require_report(run_id, request)
        check_id = digest([run_id, report["hash"]])[:32]
        value, _ = app.state.store.get(f"checks/{check_id}/request")
        if not value:
            return {"state": "not_requested"}
        return value | {"decision": app.state.store.get(f"checks/{check_id}/decision")[0]}

    def check_for_checker(check_id, request):
        if not request.state.authenticated:
            raise HTTPException(403, "Restricted investigator sign-in is required to check a review")
        value, _ = app.state.store.get(f"checks/{check_id}/request")
        if not value:
            raise HTTPException(404, "Check request not found")
        return value

    @app.get("/api/checks/{check_id}")
    def check_detail(check_id: str, request: Request):
        value = check_for_checker(check_id, request)
        run, _ = app.state.store.get(f"runs/{value['run_id']}")
        report, _ = app.state.store.get(f"reports/{value['run_id']}/1")
        review, _ = app.state.store.get(f"reviews/{value['run_id']}/1")
        if not run or not report or report["hash"] != value["report_hash"]:
            raise HTTPException(409, "Pinned report for this check is unavailable")
        manifest, _ = app.state.store.get(f"inputs/{run['case_id']}/{report['input_hash']}")
        snapshot = snapshot_from_manifest(manifest)
        view = build_export_view(snapshot.case, report, snapshot, review)
        return value | {"decision": app.state.store.get(f"checks/{check_id}/decision")[0],
                        "is_maker": owner_hash(request.state.owner) == value["maker"],
                        "report_view": view.model_dump(mode="json")}

    @app.post("/api/checks/{check_id}/decision")
    def check_decision(check_id: str, body: CheckDecision, request: Request):
        value = check_for_checker(check_id, request)
        if owner_hash(request.state.owner) == value["maker"]:
            raise HTTPException(403, "The checker must be a different investigator than the maker")
        if body.report_hash != value["report_hash"]:
            raise HTTPException(409, "Report version or hash changed")
        decision = body.model_dump() | {
            "check_id": check_id, "checker": owner_hash(request.state.owner),
            "maker_action": value["maker_action"],
            "outcome": "four_eyes_confirmed" if body.decision == "concur" else "escalated_disagreement",
            "at": datetime.now(timezone.utc).isoformat()}
        try:
            app.state.store.put(f"checks/{check_id}/decision", decision)
        except Conflict as exc:
            raise HTTPException(409, "This check already has an immutable decision") from exc
        return decision

    @app.get("/api/triage")
    def triage(request: Request):
        """Rank the actor's latest completed run per case by the recorded triage policy."""
        keys, cursor = app.state.store.scan_keys("runs/", limit=100)
        latest = {}
        for key in keys:
            run, _ = app.state.store.get(key)
            if not run or run.get("status") not in ("awaiting_review", "completed_with_gaps"):
                continue
            rid = run.get("run_id") or key.removeprefix("runs/")
            try:
                owned_run(request, rid)
            except HTTPException:
                continue
            report, _ = app.state.store.get(f"reports/{rid}/1")
            if not report:
                continue
            when = report.get("created_at", "")
            if run["case_id"] not in latest or when > latest[run["case_id"]][0]:
                latest[run["case_id"]] = (when, rid, report)
        items = []
        for case in cases.values():
            entry = latest.get(case.id)
            if not entry:
                items.append({"case_id": case.id, "title": case.title, "state": "not_investigated",
                              "score": None, "level": None, "contributors": []})
                continue
            when, rid, report = entry
            review, _ = app.state.store.get(f"reviews/{rid}/1")
            check_id = digest([rid, report["hash"]])[:32]
            decision, _ = app.state.store.get(f"checks/{check_id}/decision")
            # Reports created before the triage policy existed are scored from their evidence.
            priority = report.get("priority") or follow_up_priority(
                [Evidence.model_validate(e) for e in report.get("evidence", [])])
            items.append({"case_id": case.id, "title": case.title, "state": "investigated",
                          "run_id": rid, "report_created_at": when,
                          "score": priority.get("score"), "level": priority.get("level"),
                          "contributors": priority.get("contributors", []),
                          "review": (review or {}).get("action", "pending"),
                          "check": (decision or {}).get("outcome")})
        items.sort(key=lambda i: (i["state"] != "investigated", -(i["score"] or 0),
                                  i["review"] != "pending" if i["state"] == "investigated" else 0,
                                  i["case_id"]))
        return {"items": items, "next_cursor": cursor,
                "policy": "Demonstration triage score from recorded indicators, policy version 1. "
                          "Not a probability or finding of criminality.",
                "scope": "Latest completed run per case for this actor; child snapshots appear "
                         "under their case."}
