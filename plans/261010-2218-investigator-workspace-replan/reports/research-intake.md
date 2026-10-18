---
title: "Research: new-data intake, follow-up and history replan"
date: 2026-10-10
timezone: Asia/Ho_Chi_Minh
status: complete
---

# Research: new-data intake, follow-up and history replan

## Outcome

The simplest implementable route is one authenticated, owner-scoped follow-up
aggregate that stages CSV/PDF/JSON input, quarantines anything unresolved,
commits an immutable child snapshot, and optionally starts one linked run in the
same request. Keep the existing anonymous demo/review path unchanged. Add a
server-owned history index and three read-only report representations (JSON,
HTML, PDF) over the same immutable report. Do not create a second case database
or a background worker for the October 17 prototype.

This is a replan, not an implementation claim. The request is for all ten
workspace feature groups before October 17; follow-up includes new-data
collection. New input means actual uploaded bytes/records, including fictional
CSV/PDF/JSON additions, with provenance and review status preserved. It does
not authorize provider acquisition, URL fetching, or enterprise retention/
tenant administration.

## Evidence and load-bearing gaps

| Finding | Evidence | Consequence |
|---|---|---|
| The case universe is static. | `CASES = demo_cases()` and `case_or_404` only consult it (`backend/casemind/main.py:19,69-72`); the generator emits exactly five scenarios (`backend/casemind/generator.py:10,136-147`). | Imported child cases cannot be resolved by current `/api/cases/*` routes. Add a manifest-backed resolver that returns demo cases only to anonymous users and owner-owned imported snapshots to authenticated users. |
| Session ownership is bearer-cookie ownership. | Cookie generation and same-value check are in `backend/casemind/main.py:37-67,77-94`; tests only prove stranger denial for a different cookie (`tests/test_store_api.py:78-82`). | It is adequate for anonymous synthetic review, never for upload authority. Authenticated follow-up must carry an allowlisted Google `sub` in a signed expiring session. |
| Follow-up is only a review action. | `ReviewRequest.action` includes `needs_follow_up`, but no follow-up model exists (`backend/casemind/models.py:163-181`). | Add a lifecycle object bound to parent run/report/snapshot and originating finding/question; its staged intake is part of the follow-up, not a separate import feature. |
| There is no history index. | `FileStore`/`GCSStore` expose get/put plus CAS (`backend/casemind/store.py:14-97`); the UI retains only one latest key in local storage (`frontend/src/main.tsx:49-71`). | Add an owner-scoped CAS index with operation IDs, status, parent/child hashes and recovery state. Never enumerate object storage for authorization. |
| Cloud loading and PDFs are demo-shaped. | `Cloud.load_case` writes only transaction rows and generates PDFs from `Document` fields at `backend/casemind/cloud.py:54-97`; extraction always calls `document_pdf(doc)` (`backend/casemind/cloud.py:128-146`). | Store uploaded original bytes and hash per snapshot/document; make extraction and PDF retrieval consume that immutable object. Keep generated demo PDFs as a compatibility adapter. |
| Run sources are correctly hash-pinned but only if a manifest exists. | `pinned_case` validates manifest hash and reconstructed `Case` (`backend/casemind/main.py:96-108`); the reliability test proves current-case changes do not alter a pinned run (`tests/test_reliability.py:58-103`). | Child manifests must retain `parent_snapshot_hash`, provenance and object generations. Existing reports, evidence, assessments and reviews must remain byte-for-byte unchanged. |
| Existing protection does not include authenticated GIS. | Cross-site writes are rejected and CSP is self-only (`backend/casemind/main.py:37-67`); `pyproject.toml` has no direct auth/multipart/content-aware PDF dependency (`pyproject.toml:9-16`). | Add the verified token endpoint, configured audience/allowlist/signing secret, GIS CSP origin, multipart parser and a parser tested against actual PDF bytes. |

The Google server-side guide requires the POST `credential` plus double-submit
CSRF check, validates signature, audience, issuer and expiry, and uses `sub` as
the stable account identifier; email is not an identifier. See the [official
verification guide](https://developers.google.com/identity/gsi/web/guides/verify-google-id-token)
(updated 2025-12-22; lines 63-70,80-106,217-254). The old phase plan already
captures the same authentication boundary and anonymous compatibility
requirement (`plans/261010-2210-investigator-workspace/phase-04-follow-up-history.md:30-70`).
Carry forward `source_kind: synthetic` for fictional inputs and add separate
upload-origin/object metadata for actual uploaded bytes; do not invent a new
source-kind enum.

## Recommended contract

1. `FollowUp` is owner-scoped and immutable by event/version. It stores parent
   `run_id`, `report_hash/version`, `parent_snapshot_hash`, source finding or
   question, notes, outstanding requests, idempotency key, staged artifact IDs,
   quarantine IDs, accepted counts, child snapshot hash and linked run ID.
   Anonymous users may keep the existing `needs_follow_up` review action; notes
   or new-data intake require the authenticated route.
2. `POST /api/auth/google` verifies the GIS credential and CSRF cookie, checks
   configured audience/issuer/expiry and allowlisted `sub`, then issues a short
   lived Secure/HttpOnly/SameSite session. Keep anonymous cookie sessions for
   preloaded synthetic cases. Permit an explicit, same-browser ownership handoff
   from an anonymous parent run to the authenticated follow-up; otherwise a
   child must not be attachable merely by guessing a run ID.
3. Intake is bounded and content-aware: CSV transactions (≤2 MiB/5,000 rows),
   structured JSON records (≤1 MiB/1,000 records), each PDF (≤10 MiB), at most
   ten documents/50 pages per follow-up. Parse Decimal strings and timezone-aware
   timestamps; validate account/entity/document/watchlist links and stable IDs.
   Preserve raw row/document hash and locator. Unknown, missing or conflicting
   identity data is quarantined with the complete source item and reason; never
   auto-merge or fetch a URL. Preserve `source_kind: synthetic` for fictional
   records and add upload-origin/provenance metadata for actual bytes. These
   limits match the old phase contract
   (`phase-04-follow-up-history.md:72-77`) and remain suitable for the deadline.
4. Commit copies the parent manifest and applies only accepted records into a
   canonical child `Case` snapshot. A correction may supersede a logical record
   in the child while the parent record/object remains unchanged; comparisons use
   `(snapshot_hash, record_id)` rather than list position. Every descendant
   manifest, follow-up, run and artifact checks the authenticated owner and the
   parent owner before serving or writing.
5. Uploaded PDFs retain original bytes, media type, byte hash, page count and
   object generation. `Document` metadata points to this object; extraction
   records raw hash, processor/version, page/text anchors and confidence. The
   PDF route verifies the stored hash before returning bytes. Generated
   `document_pdf` remains only for demo snapshots, so original reports cannot
   silently fall back to regenerated content.
6. Execute is an explicit follow-up action. Reserve a generalized operation
   ledger entry and history slot before provider work, acquire one owner-scoped
   lease, create the child run, and finish inside the existing request deadline.
   Repeated idempotency returns the same follow-up/child/run. Provider failure
   retains the reservation and marks the operation failed; restart reconciliation
   marks orphaned index entries failed without invoking providers.
7. History lists owner-index entries and exposes semantic snapshot/report diffs.
   Exports use one canonical report object: existing JSON remains available;
   add escaped self-contained HTML and server-generated PDF, each labeling
   provenance, hypothesis/verification status, gaps and human review. No export
   reads current mutable case data when a run has a pinned snapshot.

## Work sequence and verification

Deliver the shared contract first, then auth/ownership and CAS history, then
CSV/JSON/PDF staging and quarantine, then child commit plus linked execution,
then history/diff and exports, with the ten workspace views consuming these
contracts. Focused tests should cover malformed/oversize inputs, cross-case
links, conflicting IDs, PDF byte/hash preservation, descendant owner denial,
anonymous upload denial, GIS verifier fixtures, duplicate operations, CAS
conflicts, restart/orphan recovery, and byte equality of every old artifact.
Run the existing store/reliability tests before the new intake/continuity tests,
then ruff, frontend typecheck/build, and the scenario evaluation gate.

Bottom-up estimate, assuming one engineer, existing frontend patterns, no OAuth
client provisioning or cloud IAM work, and no new worker: contracts and
snapshot/ownership model 8–12h; auth/CSP/session 6–10h; CSV/JSON validation and
quarantine 12–18h; PDF byte storage/extraction adapter 10–16h; follow-up,
ledger, child commit and in-request execution 14–20h; history/recovery/diff
8–12h; JSON/HTML/PDF exports and UI wiring 12–18h; focused tests and full gates
12–18h. Total: **82–124 person-hours**. External prerequisites are a configured
GIS client/audience, allowlisted `sub`, signing secret, and a tested PDF parser.
Until those prerequisites are supplied, authenticated intake remains disabled
while the anonymous demo continues to work; this is an environment prerequisite,
not a provenance restriction.

## Ranked decisions and unresolved questions

1. Use one follow-up aggregate and one manifest-backed child snapshot (lowest
   duplication and preserves existing evidence semantics).
2. Use verified Google `sub` plus signed app session for intake while retaining
   anonymous demo/review (meets the restricted-upload requirement without an
   enterprise portal).
3. Use API-mediated immutable object refs for original PDFs and canonical
   JSON-derived HTML/PDF exports (preserves provenance and old artifact bytes).

Future product decision: whether a later deployment should permit real
personal/regulated data and what retention/deletion policy would govern it.
That question is outside this synthetic-input prototype and does not block the
requested fictional CSV/PDF/JSON intake.

Status: DONE
Summary: New-data intake, follow-up and history architecture and concrete implementation gaps are documented with source evidence, ranked choices, acceptance tests and bottom-up estimates.
Concerns/Blockers: Auth client/audience, allowlisted Google subject, and PDF parser choice are external prerequisites; no cloud setup or paid API calls were performed. Real-person data policy remains future scope.
