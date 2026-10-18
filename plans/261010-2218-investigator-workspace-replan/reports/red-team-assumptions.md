# Red-team assumptions and scope audit

## Scope

Plan-only review of the index, six phases, two research reports, and the specified backend, frontend, evaluator, and cloud-setup files. No implementation files were changed and no tests, lint, typecheck, or build were run. Fixed scope remains all ten groups, actual synthetic CSV/structured/PDF intake, five scenarios, and JSON/HTML/PDF exports.

## Critical findings

### 1. The accepted transaction intake can never complete a live investigation

**Plan location:** Phase 4, **Auth, ownership and persistence contracts**, items 4 and 6 (`phase-04-follow-up-intake-history.md:29,31`), and **Done** (`:92-93`); Phase 6 live five-scenario gate (`phase-06-verification-release.md:25-33`).

Phase 4 accepts up to 5,000 CSV transactions and requires the child to publish before investigation. The live query is hard-limited to 500 rows and then rejects any result whose row count differs from the case transaction count (`backend/casemind/cloud.py:103,118-125`). A valid child with 501–5,000 transactions will publish, then fail every transaction specialist run as “snapshot incomplete”; the advertised intake bound and five-scenario live gate are therefore incompatible.

**Suggested fix:** Add an explicit Phase 1/4 contract for bounded pagination or chunked retrieval that returns every transaction in the pinned snapshot, with a deterministic global order and coverage metadata. Keep the 5,000-record accepted scope; update `cloud.py` ownership and tests to exercise 500, 501, and 5,000 records, parallel timestamps, page-boundary ordering, and proof that analytics received the full pinned set.

## High findings

### 2. Child BigQuery publication is not recoverable after a partial success

**Plan location:** Phase 4, **Auth, ownership and persistence contracts**, item 6 (`phase-04-follow-up-intake-history.md:31`), **Implementation steps**, items 7-8 (`:63-64`), and restart gate (`:75`).

The plan says to publish, verify, and recover without replaying providers, but it does not define publication reconciliation. Today `load_case` treats the manifest as the only completion marker (`backend/casemind/cloud.py:54-59`), creates the table with `WRITE_EMPTY` (`:73-76`), writes documents afterward (`:80-91`), and commits the manifest last (`:92-97`). A crash after table creation but before the manifest makes retry attempt the same non-empty table creation; a manifest that survives while a table/object is missing is trusted without checking either resource. Dynamic child execution can become permanently failed or query stale/incomplete infrastructure after restart.

**Suggested fix:** Make cloud publication an explicit resumable state machine keyed by full `SnapshotRef`. On retry, inspect and verify the existing table schema, snapshot label/hash, row count/content identity, and every exact-generation document object; create only missing resources, fail closed on mismatches, and commit the manifest only after verification. Add crash points after table load, each object write, and manifest write, plus a missing-resource-after-manifest case.

### 3. “Structured JSON records” has no executable schema for a linked Case

**Plan location:** Phase 4, **Auth, ownership and persistence contracts**, items 4-5 (`phase-04-follow-up-intake-history.md:29-30`), **Implementation steps**, items 5-6 (`:61-62`), and intake completion criterion (`:92`).

The plan caps “structured JSON” at 1,000 records but never defines its allowed record kinds, envelope, cross-file dependency order, duplicate/supersession semantics, or whether one commit validates the whole staged batch. The actual `Case` contains six distinct collections (`backend/casemind/models.py:85-90`) and rejects accounts, transactions, relationships, and documents whose referenced entities/accounts are absent (`:120-131`). A transaction CSV plus JSON account/entity additions and PDF metadata can be valid only as one batch; file-by-file validation will quarantine valid forward references, while merge-order-dependent validation produces different child hashes from the same staged set.

**Suggested fix:** Define a versioned intake batch manifest with typed envelopes for entity, account, transaction, relationship, document, and watchlist records; canonical file/object ordering; stable-ID collision and supersession rules; and one deterministic dependency-validation pass over parent plus all staged records. Quarantine must retain each original item while recording batch-level dependency failures. Test permuted upload order and mixed files yielding the same child hash and disposition.

### 4. Phase 2 persists owner-bound assessments before the Actor transition exists

**Plan location:** Phase 2, **API and UI contracts**, item 3 (`phase-02-workspace-screening-reasons.md:27`), **Implementation steps**, item 3 (`:54`), and parallelization claim (`:48`); Phase 4 actor/claim contracts (`phase-04-follow-up-intake-history.md:26-28`).

Phase 2 and Phase 4 are declared parallel after Phase 1, yet Phase 2 must store assessments “by owner” while the authenticated `Actor`, session rotation, and anonymous-to-`sub` claim are introduced only in Phase 4. Current authorization is equality against the anonymous cookie (`backend/casemind/main.py:39-42,77-80`), runs persist that raw session (`:231-239`), and reviews record only the constant label `session investigator` (`:335-340`). An assessment created before sign-in can remain keyed to the obsolete cookie, disappear from authenticated history/export, or be copied without a defined claim rule.

**Suggested fix:** Move the minimal versioned `ActorRef` and owner-alias/claim contract into Phase 1, or make Phase 2 depend on Phase 4. Require assessments, reviews, follow-ups, Q&A, exports, and history to resolve the same durable owner identity, and explicitly include assessment/review artifacts in the atomic one-time claim. Test creation before sign-in, claim, cookie rotation, sign-out/relogin, replay, and cross-owner denial.

### 5. The page budget still counts documents while the new intake promises multi-page PDFs

**Plan location:** Phase 4 limits and shared page capacity (`phase-04-follow-up-intake-history.md:29,31`), PDF verification gate (`:75`), and Phase 6 live Document AI gate (`phase-06-verification-release.md:28-30,85`).

The accepted scope allows up to ten PDFs and fifty pages per follow-up, but the existing provider reservation consumes one ledger entry per PDF hash immediately before processing (`backend/casemind/cloud.py:128-141`). The ledger calls that collection `pages` and caps its length, yet appends only one hash per call (`backend/casemind/store.py:126-134`). Unless the plan changes this contract, a fifty-page PDF consumes one “page,” so live Document AI usage can exceed the intended page budget and global/session/owner accounting will be false.

**Suggested fix:** Add `reserve_document_pages(operation_id, pdf_hash, verified_page_count)` to the Phase 4 ledger contract, atomically reserve the actual count before Document AI, and bind retries to the same operation without double-counting. Define how parser page counts are verified before the provider call and reject any mismatch returned by extraction. Cover one fifty-page PDF, ten five-page PDFs, concurrent reservations, retry, and aggregate-cap exhaustion.

## Scope and estimate audit

No feature cut is justified. The plan correctly labels 180–248 hours as a low-confidence judgment rather than measured velocity, and the research explicitly says it lacks a task inventory and integration allowance (`reports/research-foundations.md:10-17`). Findings 1-5 add missing acceptance work inside existing phases; they do not add enterprise workflow or change the fixed formats/input decision. Recalibration after Phase 1 must include full-set transaction retrieval, publication crash recovery, typed batch intake, actor migration, and real page accounting before retaining the Phase 4 and Phase 6 ranges.

## Unresolved questions

None. Each correction is a plan-level contract required to make the accepted scope executable.

Status: DONE_WITH_CONCERNS
Summary: Five load-bearing assumptions remain: intake exceeds the live query cap, cloud publication cannot reconcile partial snapshots, structured intake lacks a deterministic linked-record batch contract, assessment ownership precedes actor identity, and multi-page PDFs are charged as one page.
Concerns/Blockers: Findings 1-4 should block plan approval; finding 5 must be closed before any authorized live Document AI gate.
