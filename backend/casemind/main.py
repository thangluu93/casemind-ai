import asyncio
import hashlib
import logging
import os
import secrets
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.staticfiles import StaticFiles

from .cloud import Cloud
from .generator import demo_cases
from .investigation import investigate
from .models import ActorRef, ReviewRequest, StartRun
from .case_resolver import CaseResolver, snapshot_from_manifest
from .auth import Sessions, owner_hash
from .continuity import Operations, index_run
from .workspace_routes import register_workspace_routes
from .insight_routes import register_insight_routes
from .store import Conflict, FileStore, UsageLedger, mutate

CASES = demo_cases()


def build_app(store=None, cloud=None):
    @asynccontextmanager
    async def lifespan(app):
        if store is None:
            app.state.cloud = Cloud() if os.getenv("CASEMIND_CLOUD") == "true" else None
            app.state.store = (
                app.state.cloud.store if app.state.cloud else FileStore(Path("artifacts/local"))
            )
        else:
            app.state.store, app.state.cloud = store, cloud
        app.state.ledger = UsageLedger(app.state.store)
        app.state.operations = Operations(app.state.store, app.state.ledger)
        app.state.resolver = CaseResolver(app.state.store, CASES)
        secret = os.getenv("CASEMIND_SESSION_SECRET", "")
        audience = os.getenv("CASEMIND_GOOGLE_CLIENT_ID", "")
        subjects = [s.strip() for s in os.getenv("CASEMIND_INVESTIGATOR_SUBJECTS", "").split(",") if s.strip()]
        app.state.sessions = Sessions(app.state.store, secret, audience, subjects) if secret and audience and subjects else None
        yield

    app = FastAPI(title="CaseMind AI", lifespan=lifespan)

    @app.middleware("http")
    async def session_and_headers(request: Request, call_next):
        sid = request.cookies.get("casemind_session", "")
        if len(sid) != 64 or any(c not in "0123456789abcdef" for c in sid):
            sid = secrets.token_hex(32)
        request.state.session = sid
        request.state.authenticated = False
        request.state.owner = sid
        auth_cookie = request.cookies.get("casemind_auth")
        if auth_cookie and app.state.sessions:
            try:
                request.state.owner = app.state.sessions.resolve(auth_cookie)
                request.state.authenticated = True
            except PermissionError:
                return Response("Authenticated session expired or revoked", status_code=401)
        revoked, _ = app.state.store.get("claimed-sessions/" + owner_hash(sid))
        if revoked and not request.state.authenticated:
            sid = secrets.token_hex(32)
            request.state.session = sid
            request.state.owner = sid
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            origin = request.headers.get("origin")
            if request.headers.get("sec-fetch-site") == "cross-site" or (
                origin and origin != f"{request.url.scheme}://{request.url.netloc}"
            ):
                return Response("Cross-site write rejected", status_code=403)
        if request.headers.get("content-type", "").startswith("application/json") and not request.url.path.endswith("/intake"):
            chunks, size = [], 0
            async for chunk in request.stream():
                size += len(chunk)
                if size > 1024 * 1024:
                    return Response('{"detail":"JSON request exceeds one MiB"}', status_code=413, media_type="application/json")
                chunks.append(chunk)
            request._body = b"".join(chunks)
        response = await call_next(request)
        if request.cookies.get("casemind_session") != sid:
            response.set_cookie(
                "casemind_session",
                sid,
                httponly=True,
                samesite="strict",
                secure=request.url.scheme == "https",
                max_age=86400,
            )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Cache-Control"] = (
            "no-store" if request.url.path.startswith("/api") else "public,max-age=300"
        )
        response.headers.setdefault("Content-Security-Policy", (
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
        ))
        if app.state.sessions and "sandbox" not in response.headers["Content-Security-Policy"]:
            response.headers["Content-Security-Policy"] = response.headers["Content-Security-Policy"].replace("script-src 'self'", "script-src 'self' https://accounts.google.com/gsi/").replace("frame-src 'self'", "frame-src 'self' https://accounts.google.com/gsi/").replace("connect-src 'self'", "connect-src 'self' https://accounts.google.com/gsi/")
        return response

    def actor(request):
        return ActorRef(kind="google" if request.state.authenticated else "session", owner_id=request.state.owner)

    def snapshot_or_404(case_id, request):
        try:
            return app.state.resolver.resolve(case_id, actor(request))
        except KeyError as exc:
            raise HTTPException(404, "Case not found") from exc
        except ValueError as exc:
            raise HTTPException(409, "Source snapshot integrity failed") from exc

    def case_or_404(case_id, request):
        return snapshot_or_404(case_id, request).case

    def public_run(run):
        return {key: value for key, value in run.items() if key not in ("session", "owner_id")}

    def owned_run(request, run_id):
        run, version = app.state.store.get(f"runs/{run_id}")
        owned = bool(run and (run.get("owner_id") == request.state.owner or (
            not request.state.authenticated and run.get("session") == request.state.session
        ) or (request.state.authenticated and app.state.sessions.owns_run(request.state.owner, run))))
        if not owned:
            raise HTTPException(404, "Run not found")
        if run["status"] == "running" and run.get("deadline", run.get("started_epoch", 0) + 150) < time.time():
            mutate(
                app.state.store,
                f"runs/{run_id}",
                lambda v: (
                    v
                    | {
                        "status": "interrupted",
                        "error": "Process stopped before completion; start a new run.",
                    }
                ),
            )
            run, version = app.state.store.get(f"runs/{run_id}")
        return run, version

    def pinned_snapshot(request, run_id):
        run, _ = owned_run(request, run_id)
        report, _ = app.state.store.get(f"reports/{run_id}/1")
        input_hash = run.get("input_hash") or (report or {}).get("input_hash")
        if not input_hash:
            raise HTTPException(409, "Pinned source snapshot is unavailable")
        manifest, _ = app.state.store.get(f"inputs/{run['case_id']}/{input_hash}")
        if not manifest or manifest.get("hash") != input_hash:
            raise HTTPException(409, "Pinned source snapshot is unavailable")
        try:
            snapshot = snapshot_from_manifest(manifest)
        except ValueError as exc:
            raise HTTPException(409, "Pinned source snapshot integrity check failed") from exc
        return snapshot

    def pinned_case(request, run_id):
        return pinned_snapshot(request, run_id).case

    @app.get("/api/runs/{run_id}/case")
    def run_case(run_id: str, request: Request):
        return pinned_case(request, run_id).model_dump(mode="json")

    @app.get("/api/runs/{run_id}/sources/{source_id}")
    def run_source(run_id: str, source_id: str, request: Request):
        record = pinned_case(request, run_id).sources.get(source_id)
        if record is None:
            raise HTTPException(404, "Source not found in this run snapshot")
        return record.model_dump(mode="json")

    @app.get("/healthz")
    @app.get("/api/health")
    def health():
        return {"status": "ok", "synthetic_only": True}

    @app.get("/api/cases")
    def cases():
        return [
            {
                "id": c.id,
                "title": c.title,
                "description": c.description,
                "source_kind": "synthetic",
                "transaction_count": len(c.transactions),
                "document_count": len(c.documents),
                "kind": "safety_control" if c.title.endswith("safety control") else "scenario",
            }
            for c in CASES.values()
        ]

    @app.get("/api/cases/{case_id}")
    def case_detail(case_id: str, request: Request):
        return case_or_404(case_id, request).model_dump(mode="json")

    @app.get("/api/cases/{case_id}/sources/{source_id}")
    def source(case_id: str, source_id: str, request: Request):
        record = case_or_404(case_id, request).sources.get(source_id)
        if record is None:
            raise HTTPException(404, "Source not found")
        return record.model_dump(mode="json")

    @app.get("/api/cases/{case_id}/runs/{key}")
    def resolve_run(case_id: str, key: str, request: Request):
        case_or_404(case_id, request)
        run_id = hashlib.sha256(f"{request.state.owner}:{case_id}:{key}".encode()).hexdigest()[
            :32
        ]
        return public_run(owned_run(request, run_id)[0]) | {"run_id": run_id}

    @app.post("/api/cases/{case_id}/runs")
    async def start(case_id: str, body: StartRun, request: Request):
        snapshot = snapshot_or_404(case_id, request)
        if not app.state.cloud:
            raise HTTPException(
                503, "Live Google Cloud is not configured; no simulated investigation is available"
            )
        session = request.state.owner
        run_id = hashlib.sha256(f"{session}:{case_id}:{body.idempotency_key}".encode()).hexdigest()[
            :32
        ]
        existing, _ = app.state.store.get(f"runs/{run_id}")
        if existing and existing.get("input_hash") != snapshot.snapshot_id:
            raise HTTPException(409, "Run key belongs to a different input snapshot")
        if existing and not existing.get("operation_id"):
            return public_run(owned_run(request, run_id)[0]) | {"run_id": run_id}
        try:
            operation = app.state.operations.reserve(session, "investigation:" + case_id,
                body.idempotency_key, snapshot.snapshot_id, "", [],
                {"run_id": run_id, "case_id": case_id, "session": request.state.session})
        except ValueError as exc:
            raise HTTPException(429, str(exc)) from exc
        if existing or operation["state"] == "terminal":
            if existing:
                return public_run(owned_run(request, run_id)[0]) | {"run_id": run_id}
            return {"run_id": run_id, "case_id": case_id, "status": "interrupted",
                    "events": [], "error": operation.get("error") or "No completed report"}

        def acquire(value):
            if value and value["expires"] > time.time():
                raise Conflict("An investigation is already running for this actor")
            return {"operation_id": operation["id"], "expires": time.time() + 120}
        mutate(app.state.store, f"leases/{session}", acquire)
        execution = app.state.operations.begin(session, operation["id"])
        run = {"case_id": case_id, "session": request.state.session, "owner_id": session,
               "status": "running", "events": [], "started_epoch": time.time(),
               "run_id": run_id, "input_hash": snapshot.snapshot_id,
               "operation_id": operation["id"], "deadline": execution.deadline}
        app.state.store.put(f"runs/{run_id}", run)
        index_run(app.state.store, session, run_id)

        async def emit(role, status, payload=None):
            execution.check()
            def append(value):
                return value | {"events": [*value["events"], {"index": len(value["events"]),
                    "role": role, "status": status, "at": datetime.now(timezone.utc).isoformat(),
                    "payload": payload or {}}]}
            mutate(app.state.store, f"runs/{run_id}", append)
        try:
            documents = {d.id: app.state.resolver.document_bytes(snapshot, d.id)
                         for d in snapshot.case.documents}
            async with asyncio.timeout(execution.check()):
                await asyncio.to_thread(app.state.cloud.load_case, snapshot, documents, execution)
                execution.check()
                report = await investigate(snapshot, run_id, app.state.store, app.state.cloud, emit,
                        timeout=execution.check(), documents=documents, execution=execution)
                execution.check()
                mutate(app.state.store, f"runs/{run_id}", lambda value: value | {
                    "status": report["status"], "report_hash": report["hash"]})
                app.state.operations.finish(execution, result={"run_id": run_id,
                    "case_id": case_id, "status": report["status"]})
        except BaseException as exc:
            # The client sees a sanitized status; operators need the cause in service logs.
            logging.getLogger("casemind").exception("Investigation %s did not complete", run_id)
            status = "interrupted" if isinstance(exc, (asyncio.CancelledError, TimeoutError, Conflict)) else "failed"
            error = "Investigation did not complete; no substitute report generated."
            mutate(app.state.store, f"runs/{run_id}", lambda value: value | {"status": status, "error": error})
            try:
                app.state.operations.finish(execution, error=error)
            except Conflict:
                pass
            if isinstance(exc, asyncio.CancelledError):
                raise
        finally:
            mutate(app.state.store, f"leases/{session}", lambda value:
                   value | {"expires": 0} if value and value.get("operation_id") == operation["id"] else value)
        return public_run(app.state.store.get(f"runs/{run_id}")[0])

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: str, request: Request):
        return public_run(owned_run(request, run_id)[0])

    @app.get("/api/runs/{run_id}/report")
    def report(run_id: str, request: Request):
        owned_run(request, run_id)
        value, _ = app.state.store.get(f"reports/{run_id}/1")
        if value is None:
            raise HTTPException(404, "Report not ready")
        return value

    @app.get("/api/runs/{run_id}/evidence/{evidence_id}")
    def get_evidence(run_id: str, evidence_id: str, request: Request):
        owned_run(request, run_id)
        value, _ = app.state.store.get(f"evidence/{run_id}/{evidence_id}")
        if value is None:
            raise HTTPException(404, "Evidence not found")
        return value

    @app.get("/api/runs/{run_id}/review")
    def get_review(run_id: str, request: Request):
        owned_run(request, run_id)
        value, _ = app.state.store.get(f"reviews/{run_id}/1")
        return value or {"action": "pending", "version": 1}

    @app.post("/api/runs/{run_id}/review")
    def review(run_id: str, body: ReviewRequest, request: Request):
        owned_run(request, run_id)
        value, _ = app.state.store.get(f"reports/{run_id}/1")
        if (
            not value
            or value["hash"] != body.report_hash
            or value["version"] != body.expected_version
        ):
            raise HTTPException(409, "Report version or hash changed")
        result = body.model_dump() | {
            "run_id": run_id,
            "version": 1,
            "reviewer": "session investigator",
            "at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            app.state.store.put(f"reviews/{run_id}/1", result)
        except Conflict as exc:
            raise HTTPException(409, "This report version already has an immutable review") from exc
        return result

    register_workspace_routes(app, actor, snapshot_or_404, pinned_snapshot, owned_run, public_run)
    register_insight_routes(app, CASES, pinned_snapshot, owned_run)

    frontend = Path(os.getenv("CASEMIND_FRONTEND_DIR", "/app/frontend/dist"))
    if not frontend.exists():
        frontend = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    if frontend.exists():
        app.mount("/", StaticFiles(directory=frontend, html=True), name="workspace")
    return app


app = build_app()
