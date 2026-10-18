---
phase: 4
title: "Bounded follow-up, restricted intake and durable history"
status: pending
priority: P1
effort: "44-60 person-hours"
dependencies: [1]
---

# Phase 4: Bounded follow-up, restricted intake and durable history

## Goal

Persist case-linked follow-up and complete run history, including controlled new
CSV/PDF/structured evidence intake that creates a new immutable snapshot and run
without mutating any prior source, report, evidence, assessment or review.

## Context and verified foundations

- Current `needs_follow_up` is only a report disposition
  (`backend/casemind/models.py:168`); there is no executable follow-up record.
- Run ownership uses an opaque random cookie and equality check
  (`backend/casemind/main.py:37`, `backend/casemind/main.py:77`). It is not a
  verified or authenticated user identity and is unsuitable for upload authority.
- `UsageLedger.reserve_run` only accounts for investigation runs
  (`backend/casemind/store.py:100`). Runs are addressed from a browser-held latest
  key (`frontend/src/main.tsx:58`), not a server-owned history index.
- CAS retry support exists in `mutate` (`backend/casemind/store.py:88`).

## Requirements

- [ ] Follow-up supports bounded existing checks, investigator notes, outstanding
      external-record requests, and user-confirmed new input collection.
- [ ] Intake accepts investigator-selected transaction CSV, PDF documents, and
      structured additions/corrections for transactions, entity identifiers,
      relationships, documents and watchlist records. It never fetches URLs or
      purchases/joins an external watchlist automatically.
- [ ] Hosted intake requires verified Google ID token authentication, configured
      OAuth audience, server-side allowlisted stable `sub`, origin/CSRF checks and
      an expiring signed Secure/HttpOnly session. Anonymous users retain existing
      synthetic investigation/review flows, whose source inputs stay read-only;
      they cannot upload/import.
- [ ] Existing anonymous investigation/review/history behavior remains available
      for preloaded synthetic cases. Its opaque cookie is an anonymous bearer
      capability, not authenticated identity, and it never grants intake access.
- [ ] Initial intake is synthetic-only and labels provenance. Real personal or
      regulated data requires a separately authorized privacy/retention design.
- [ ] Originals are immutable. Conflicting/missing IDs are quarantined for review;
      corrections/additions produce a child snapshot linked to parent run/follow-up.
- [ ] Executing accepted intake explicitly starts a new quota-reserved analysis in
      the same request with a hard deadline; no unmanaged background execution.
- [ ] Follow-up/Q&A/run reservations share a conservative global operation ledger,
      per-session/per-user caps and operation idempotency. Provider failure retains
      its reservation.
- [ ] History is server-owned, session/user scoped, CAS-safe and recoverable after
      restart/index failure. No object-store enumeration can expose another owner.

## Authentication and intake contract

Use Google Identity Services ID tokens with server verification of signature,
issuer, audience and expiry, then bind the verified `sub` to an allowlist and a
short-lived signed app session. Follow the official
[Google web token verification guide](https://developers.google.com/identity/gsi/web/guides/verify-google-id-token)
and the pinned Python verifier behavior in
[`google.oauth2.id_token`](https://google-auth.readthedocs.io/en/latest/_modules/google/oauth2/id_token.html).
After current official API integration checks, pin `google-auth`, the multipart
parser required by FastAPI, and a content-aware PDF parser directly in
`pyproject.toml`; do not rely on transitive versions. OAuth client registration,
allowlist and signing-secret setup are prerequisites
for hosted intake and are not performed or authorized by this plan.

Default limits: CSV ≤2 MiB/5,000 rows, JSON body ≤1 MiB/1,000 records, PDF ≤10
MiB each, ≤10 documents and ≤50 total pages per follow-up. Validate content type,
actual parseability, encryption/unsupported-PDF errors, schema, timezone, Decimal
strings, identifiers and cross-record links; a PDF signature alone is insufficient.
Ignore client filenames as storage keys. Quarantine the complete rejected row plus
reason inside the same owner scope; never merge conflicting identities automatically.

## Data flow

1. An authenticated allowlisted investigator creates a follow-up bound to run,
   report hash/version and originating evidence/question.
2. Notes or outstanding requests persist without model calls. Selected files or
   structured records stream through bounded validation into an owner-scoped
   staging artifact; invalid/conflicting rows enter quarantine.
3. Investigator reviews accepted/quarantined counts and explicitly commits.
4. Commit copies the parent snapshot, applies accepted additions/corrections as a
   new immutable child snapshot, records provenance/parent hashes, and leaves the
   original untouched.
5. Execute reserves history index + global usage operation before provider work,
   creates a new linked run, and completes within the request deadline.
6. History lists owner-index entries and can compare snapshots/reports by stable
   source/derivation identities, never evidence-list position.

## Files to modify or create

| Action | Absolute path | Change |
|---|---|---|
| Modify | `/Users/thangluu/Repos/casemind-ai/pyproject.toml` | Pin verified token, multipart and PDF parsing dependencies. |
| Modify | `/Users/thangluu/Repos/casemind-ai/backend/casemind/models.py` | Follow-up, provenance, intake, quarantine, history and signed-session contracts. |
| Modify | `/Users/thangluu/Repos/casemind-ai/backend/casemind/store.py` | General idempotent operation reservations and CAS history/index primitives. |
| Create | `/Users/thangluu/Repos/casemind-ai/backend/casemind/auth.py` | Token verification, allowlist and signed session helpers. |
| Create | `/Users/thangluu/Repos/casemind-ai/backend/casemind/intake.py` | Bounded CSV/PDF/structured validation and immutable child snapshots. |
| Create | `/Users/thangluu/Repos/casemind-ai/backend/casemind/continuity.py` | Follow-up lifecycle, history index/diff and recovery logic. |
| Modify | `/Users/thangluu/Repos/casemind-ai/backend/casemind/main.py` | Add auth/follow-up/intake/history routes and call services in-request. |
| Modify | `/Users/thangluu/Repos/casemind-ai/frontend/src/api.ts` | Auth, intake, follow-up and history types. |
| Modify | `/Users/thangluu/Repos/casemind-ai/frontend/src/main.tsx` | Compose Follow-up and History destinations. |
| Create | `/Users/thangluu/Repos/casemind-ai/frontend/src/follow-up-workspace.tsx` | Notes, requests, upload/entry, quarantine review and explicit execution. |
| Create | `/Users/thangluu/Repos/casemind-ai/frontend/src/run-history.tsx` | Owner-scoped history and semantic run comparison. |
| Modify | `/Users/thangluu/Repos/casemind-ai/frontend/src/styles.css` | Intake/history/error/progress states. |
| Modify | `/Users/thangluu/Repos/casemind-ai/tests/test_store_api.py` | Ledger, signing, CAS index, restart and cross-owner tests. |
| Create | `/Users/thangluu/Repos/casemind-ai/tests/test_intake.py` | Boundary, quarantine, immutability and child-snapshot tests. |
| Create | `/Users/thangluu/Repos/casemind-ai/tests/test_continuity.py` | Idempotency, deadlines, recovery, history and diff tests. |

Proposed routes include `POST /api/auth/google`, owner-scoped follow-up CRUD,
multipart CSV/PDF intake, structured record intake, commit/execute, and
`GET /api/history`. Exact route schemas are defined by the strict models above.

## Implementation steps

1. Implement authenticated allowlisted sessions signed and expired by the server.
   Preserve the existing anonymous cookie flow unchanged for synthetic investigations
   and review, but require verified authenticated ownership on every intake route.
2. Generalize reservations to `{operation_kind, operation_id}` while reading the
   existing `runs/pages/sessions` ledger shape. Keep `reserve_run` as a compatible
   wrapper and reserve before model/Document AI calls.
3. Reserve a history index entry before run/provider work. If CAS cannot commit,
   fail closed without provider calls. Reconcile missing run artifacts as failed;
   repair legacy entries when an owned legacy run is resolved by known key.
4. Implement follow-up and content-aware intake validators with limits above,
   source provenance, quarantine and immutable parent/child snapshot hashes. Reject
   encrypted/unsupported PDFs and enforce the shared Document AI page reservation
   before extraction. Sandbox embedded PDF viewing with no external fetch or script
   execution; treat uploaded text as data that cannot direct tools. Add no runtime fake data.
5. Execute existing checks or a new child-snapshot investigation only after explicit
   confirmation, idempotency validation, reservation and lease acquisition.
6. Build follow-up/history UI with upload progress, accepted/quarantine review,
   outstanding requests, visible quotas/failures and semantic diffs.

## Verification gates

```bash
./.venv/bin/python -m pytest tests/test_store_api.py tests/test_reliability.py tests/test_intake.py tests/test_continuity.py -q
./.venv/bin/python -m ruff check backend/casemind/auth.py backend/casemind/intake.py backend/casemind/continuity.py backend/casemind/store.py backend/casemind/main.py tests/test_intake.py tests/test_continuity.py
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

Use test-only token verifier/provider boundary fixtures; runtime behavior must
still verify real tokens and invoke real providers only in an authorized live gate.

## Success criteria

- [ ] Anonymous sessions cannot intake; non-allowlisted/invalid/expired tokens fail.
- [ ] Oversize, wrong-type, malformed, conflicting and cross-case inputs fail or
      quarantine without changing the parent snapshot.
- [ ] Commit produces a new hash-linked snapshot; execution produces a new run and
      leaves every old report/evidence/review/assessment byte-for-byte intact.
- [ ] Duplicate operations do not duplicate uploads, reservations or executions.
- [ ] History survives restart/index conflicts and denies other owners.

## Risks and rollback

| Risk | Likelihood × impact | Mitigation |
|---|---|---|
| Restricted uploads expose sensitive data | High × High | Allowlisted verified identity, synthetic-only policy, strict size/type/schema, no URLs, owner scope and no logs of content. |
| Two-store writes leave orphan/index drift | Medium × High | Reserve index first, fail before providers, mark/reconcile partial artifacts through CAS. |
| New operations exceed cost budget | Medium × High | Shared conservative reservations, explicit execution and retained failed reservations. |
| OAuth setup misses deadline | High × High | Treat registered client/allowlist/secret as a named external prerequisite; intake cannot fail open. |

Feature rollback disables auth intake and execution routes while retaining immutable
artifacts for recovery. Roll back ledger reads through its compatibility wrapper;
do not delete child snapshots, quarantine records or history during rollback.

## Todo

- [ ] Implement signed/verified owner sessions and generalized reservations.
- [ ] Implement bounded intake, quarantine, child snapshots and linked execution.
- [ ] Deliver follow-up/history UI and pass security/restart/concurrency gates.
