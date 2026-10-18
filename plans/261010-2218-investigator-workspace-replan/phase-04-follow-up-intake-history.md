---
phase: 4
title: "Follow-up, intake and history"
status: completed
priority: P1
effort: "44-60 person-hours"
dependencies: [1]
---

# Phase 4: Follow-up, intake and history

## Goal

Create a persistent authenticated follow-up that streams bounded new synthetic CSV/structured/PDF data, commits an immutable child snapshot, optionally executes a linked run, and exposes history complete for the actor authority the service can prove.

## Verified context and decisions

- Anonymous bearer-cookie ownership and self-only CSP preserve demo/review but do not authorize uploads (`backend/casemind/main.py:37-67`).
- The owning architecture explicitly limits public judges to preloaded synthetic cases and requires later uploads to add authentication, content/size controls and scoped object access (`docs/system-architecture.md:118-124`). This phase implements that restricted boundary without an enterprise identity platform.
- `needs_follow_up` is only a review action and the browser remembers one latest run key (`backend/casemind/models.py:163-181`; `frontend/src/main.tsx:49-71`).
- Runs derive from session/case/key, reserve lease/usage, and execute in-request (`backend/casemind/main.py:184-297`). Imported cases must not leak into `CASES`.
- Cloud transaction query assumes `load_case` already published the table. Current callers are setup/evaluation, not investigation; child execution must publish after reservation and before tool query (`backend/casemind/cloud.py:54-126`; `evaluation/run-evaluation.py:101-111`).
- Uploaded origin is distinct from synthetic classification. Accepted choice: actual new uploaded bytes contain supplied synthetic prototype data; no notes-only shortcut and no real-person-data claim.

## Auth, ownership and persistence contracts

1. `Actor` is an anonymous capability or authenticated Google `sub`; email is display metadata. Use GIS JavaScript callback mode, then a same-origin `POST /api/auth/google` with credential plus matching CSRF cookie/body token. Keep the current cross-site middleware unchanged. Verify signature, audience, issuer, expiry and allowlisted `sub`.
2. The authenticated cookie contains only a signed high-entropy opaque session ID. `sessions/{id_hash}` stores owner `sub`, expiry, revocation/version and creation/rotation metadata. Every authenticated request loads that record, rechecks expiry/revocation and current subject allowlist, and fails closed. Login and ownership claim rotate IDs; sign-out first CAS-revokes the record, then clears the cookie. Captured pre-login/pre-claim/pre-sign-out cookies must fail, including after restart.
3. Keep public demo cases available to every actor and keep each anonymous capability’s own run/review access compatible. During same-browser sign-in, persist an old-session→`sub` proof mapping and bounded bootstrap cursor before rotating authority. Only runs whose stored anonymous session matches that proof can be durably claimed; interrupted scans resume. History is `complete_for_actor`: current anonymous capability plus durably claimed runs. Cleared/expired-cookie runs without persisted proof stay inaccessible and are excluded, not guessed.
4. `FollowUp` is an immutable event aggregate bound to owner, parent run/report/snapshot, source evidence/question, notes, requested checks, staged/quarantine objects, child snapshot and linked run. Every behavior-changing command supplies an idempotency key and expected version.
5. Enforce intake before buffering: use `Content-Length` only as an early rejection hint, stream decoded multipart bytes while hashing, and stop at CSV ≤2 MiB/5,000 rows, JSON ≤1 MiB/1,000 records, PDF ≤10 MiB each, 10 PDFs/50 pages, 32 MiB decoded per request and 64 MiB staged per follow-up. Stream only to uncommitted temporary objects; atomically promote accepted originals. Disconnect/oversize/error deletes the temp object, and a one-hour TTL sweep removes abandoned staging.
6. Parse Decimal/timezone values, validate links and retain accepted/quarantined origin, synthetic classification, locator, reason and object ref. Reject URLs, archives, auto-merges and silent drops. Commit creates a content-addressed child without changing parent bytes. Original PDFs remain attachment-only; Phase 1 preflight/derivative helpers provide page counts and separate inert lineage.
7. Compute `canonical_request_hash = digest(owner, operation_type, idempotency_key, parent_snapshot_hash, report_version/hash, sorted source-hash set, normalized parameters or question)`. The deterministic operation ID derives from owner/type/key. Equal hash returns the same operation; unequal reuse returns 409 before quota. Apply this to follow-up execution and Phase 5 Q&A.
8. Write `operations/{owner_hash}/{operation_id}/request` first as the immutable envelope, then maintain one CAS manifest plus immutable appended events through `reserving → ready → executing → terminal`. Quota and history are idempotent projections keyed by operation ID. Bounded owner-prefix scan can rediscover an operation if projection writes crash. Provider work starts only after quota/history projections confirm `ready`.
9. One absolute deadline (120 seconds) covers child publication plus investigation, leaving margin below the current 150-second stale threshold. The lease expires after that deadline and carries a monotonically increasing fence; every cloud/provider boundary and terminal write verifies owner, deadline, manifest state and fence. Every I/O/provider timeout uses the remaining budget. No renewal loop, worker or indefinite lease is added.
10. Execute publishes through `Cloud.load_case`, verifies snapshot/table/object identity, then investigates. Recovery scans operation manifests, repairs idempotent quota/history projections, and marks expired `executing` operations interrupted; it never invokes providers. Semantic diff keys by snapshot+record IDs, source hashes, evidence tool/version/claim, report hash and review.
11. One versioned `IntakeBatch` envelope contains typed `entities`, `accounts`, `transactions`, `relationships`, `documents` and `watchlist` records plus each `add|supersede` action, target stable ID/revision and source object. CSV rows, structured JSON and PDF metadata join the same batch. Canonical object/record ordering makes upload order irrelevant. Validate parent plus the entire staged accepted set in dependency order; quarantine retains originals and batch-level reasons. Commit succeeds only when the accepted subset is internally complete with no dangling ID or silent partial merge.
12. Cloud publication is keyed by full `SnapshotRef`. Persist a publication intent and deterministic BigQuery job ID before submission. On explicit retry, inspect the existing job/table/schema/snapshot label, exact row count/content hash and document generations before creating only a proven-missing resource; never blindly replay `WRITE_EMPTY`. Commit the input manifest only after verification. Restart recovery is read-only and marks uncertain work interrupted; a resource missing after manifest commit fails closed until an explicit reserved repair action.
13. Preflight each PDF with the pinned parser and atomically reserve `verified_page_count` immediately before every Document AI provider attempt. Duplicate operation replay makes no new attempt/reservation. An explicit provider retry reserves the actual page count again because the earlier call may have been billed. Provider page-count mismatch becomes a retained failure with no quota refund. Legacy one-hash reservations remain compatible as one-page entries.

## Files and ownership

| Action | Absolute path | Owner/change |
|---|---|---|
| Modify | `/Users/thangluu/Repos/casemind-ai/backend/casemind/models.py` | Integration owner: actor/follow-up/intake/operation/history contracts. |
| Create | `/Users/thangluu/Repos/casemind-ai/backend/casemind/auth.py` | Backend lane: GIS, signed sessions, ownership claim. |
| Create | `/Users/thangluu/Repos/casemind-ai/backend/casemind/intake.py` | Backend lane: typed batch, streaming staging, whole-batch validation/quarantine/commit. |
| Create | `/Users/thangluu/Repos/casemind-ai/backend/casemind/continuity.py` | Backend lane: operation state machine, fencing, projections, recovery, scoped history/bootstrap/diff. |
| Modify | `/Users/thangluu/Repos/casemind-ai/backend/casemind/investigation.py` | Backend lane: resolved child inputs/generalized reservation. |
| Modify | `/Users/thangluu/Repos/casemind-ai/backend/casemind/main.py` | Integration owner: auth/follow-up/intake/history and CSP. |
| Create | `/Users/thangluu/Repos/casemind-ai/tests/test_intake_history.py` | Backend lane: auth/intake/ownership/migration/restart/diff. |
| Modify | `/Users/thangluu/Repos/casemind-ai/tests/test_reliability.py` | Recovery/lease/original-byte regressions. |
| Modify | `/Users/thangluu/Repos/casemind-ai/tests/test_store_api.py` | Owner index/CAS/quota regressions. |
| Modify | `/Users/thangluu/Repos/casemind-ai/frontend/src/api.ts` | Integration owner: continuity contracts. |
| Create | `/Users/thangluu/Repos/casemind-ai/frontend/src/follow-up-workspace.tsx` | UI lane: tasks/staging/quarantine/execute/failures. |
| Create | `/Users/thangluu/Repos/casemind-ai/frontend/src/case-history.tsx` | UI lane: history/bootstrap progress/diff. |
| Modify | `/Users/thangluu/Repos/casemind-ai/frontend/src/main.tsx` | Integration owner: identity/continuity composition. |
| Modify | `/Users/thangluu/Repos/casemind-ai/frontend/src/styles.css` | Integration owner: responsive states. |
| Modify | `/Users/thangluu/Repos/casemind-ai/pyproject.toml` | Integration owner: verified pinned auth/multipart dependencies; reuse Phase 1 renderer pin. |

## Implementation steps

1. Verify official GIS callback/token and multipart APIs, then pin their dependencies. Reuse Phase 1 PDF preflight/derivative helper. Allow exact GIS script/frame/connect origins while retaining the global cross-site write guard; login credential POST remains same-origin.
2. Implement opaque server-side sessions, rotation/revocation and per-request allowlist checks. Persist claim proof/cursor before authority rotation; prove public demos remain available to authenticated actors.
3. Implement streaming multipart counters/temp objects/promotion/TTL before parsers. Hash while streaming, cap decompressed/rendered PDF resources, and keep originals attachment-only.
4. Add immutable follow-up events and versioned `IntakeBatch`. Canonicalize mixed CSV/JSON/PDF records, apply explicit add/supersede revisions, validate all cross-record dependencies over parent+batch, and commit only the valid accepted set atomically; creating a task/note never calls providers.
5. Implement canonical request hashing and operation envelope/manifest/events first. Project quota/history idempotently, then move to `ready`; unequal key reuse fails before quota.
6. On explicit execute, acquire a 120-second fenced lease and persist publication intent/job ID. Transition to `executing`, reconcile or publish/verify the full child (≤5,000 total transactions), create linked run, then investigate using remaining-time subcall deadlines. Verify fence before each provider boundary/write.
7. Add crash injection after request, each state CAS, quota projection, history projection, lease, publication and terminal write. Recovery finds owner-prefixed operations, repairs metadata and never replays providers.
8. Before every Document AI attempt, verify parser page count and reserve that many pages atomically. Explicit retries reserve again; duplicates do not call/reserve again. Implement `complete_for_actor` history/bootstrap, semantic diff and UI disclosure.

## Verification

```bash
./.venv/bin/python -m pytest tests/test_intake_history.py tests/test_store_api.py tests/test_reliability.py tests/test_investigation.py -q
./.venv/bin/python -m ruff check backend/casemind tests/test_intake_history.py
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

Test foreign origin/fetch metadata and CSRF mismatch; copied cookies/rotation/restart; chunked/no-length multipart, aggregate/disconnect/TTL; active/malformed PDFs; permuted mixed batches and forward refs; add/supersede collision/dangling IDs; 5,000 total limit; canonical-hash conflicts; slow publication/fence; crash after every CAS/publication point; uncertain/missing-after-manifest resources; one 50-page and ten 5-page PDFs, concurrent caps, duplicate versus explicit retry/mismatch; interrupted claims/lost cookie/restart/old bytes.

## Risks and rollback

| Risk | Likelihood × impact | Mitigation |
|---|---|---|
| GIS/CSP fails or weakens policy | High × High | Official check, exact allowlist, auth off by default, anonymous regression. |
| Copied session survives sign-out | Medium × High | Opaque ID plus Store revocation/expiry/version and per-request lookup. |
| Upload exhausts memory/disk/storage | Medium × High | Pre-buffer stream/aggregate caps, temp promotion, disconnect cleanup and TTL. |
| Partial CAS sequence loses authority | High × High | Operation manifest authority, owner-prefix discovery and idempotent projections. |
| Lease expires during valid execution | High × High | One 120-second deadline, remaining-time subcalls and fence checks. |
| Legacy bootstrap overclaims history | Medium × High | Proof mapping before rotation and `complete_for_actor` boundary. |
| Partial cloud publication cannot resume safely | Medium × High | SnapshotRef intent/job ID, explicit reconciliation and fail-closed repair. |
| Mixed intake becomes order-dependent/dangling | Medium × High | Typed canonical batch and whole accepted-set dependency validation. |
| Multi-page provider spend is undercounted | Medium × High | Verified page-count reservation per actual provider attempt. |

Back up persistent state/checksums before migration. Rollback disables auth/intake and restores exact backup; staged objects remain quarantined. Never use Git checkout for data rollback.

## Done

- [x] Auth sessions are revocable server-side; public demos and proven ownership transitions are tested.
- [x] Streaming synthetic CSV/JSON/PDF intake is bounded before buffering, immutable, inertly rendered and clean after failure.
- [x] Canonical-hash operations are fenced, deadline-bound, projection-recoverable and never replay providers.
- [x] History is complete for the current/proven actor boundary and never claims lost-cookie runs.
- [x] Mixed intake commits the same valid child regardless of upload order; cloud publication and actual page spend are reconcilable/auditable.

## Execution evidence

Completed locally on 2026-10-11. See the [execution report](../reports/cook-261011-1326-investigator-workspace.md)
and [independent review](../reports/code-review-261011-workspace.md).
Provider behavior and deployed authentication remain Phase 6 live gates.
