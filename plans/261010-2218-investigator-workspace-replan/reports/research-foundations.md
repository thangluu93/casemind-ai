---
title: "Replan foundations: local reuse, critical path and estimate basis"
date: 2026-10-10
timezone: Asia/Ho_Chi_Minh
status: complete
---

# Result

The existing `180–248` human-hour range has a defensible phase-level shape, but
it is not a measured bottom-up forecast. It is the exact sum of six manually
assigned ranges (24–32, 24–32, 28–40, 44–60, 36–48, 24–36), and the plan maps
each range to concrete files, contracts, gates and dependencies
([plan.md:41-57](../../261010-2210-investigator-workspace/plan.md#L41)). There is
no completed task inventory, velocity evidence or integration allowance. Keep it
as an order-of-magnitude planning band with low confidence for continuity and
Q&A/exports, rather than call it validated capacity.

The arithmetic behind six to nine additional builders is correct: two builders
at four productive hours per day for six days provide about 48 hours, leaving
132–200 hours; at 24 hours per added builder over those six days this requires
six to nine additions ([plan.md:73-76](../../261010-2210-investigator-workspace/plan.md#L73)).
That is necessary aggregate capacity, not a schedule proof. Shared edits to
`models.py`, `main.py`, `api.ts`, `main.tsx` and `styles.css` must be serialized
([phase-06:145-151](../../261010-2210-investigator-workspace/phase-06-evaluation-release-readiness.md#L145)),
and the dependency critical path remains substantial.

# What is reusable

| Area | Concrete reuse | Actual delta |
|---|---|---|
| Source and run scope | Current case and pinned-run source routes already validate the pinned manifest and hash (`main.py:96-119`); PDF access also checks the snapshot hash (`main.py:121-145`). | Typed inventory/selection views, scope labels, missing/error states and candidate assessment routes. |
| Deterministic facts | `transaction_analysis` already composes flow, structuring and activity checks (`analytics.py:197-203`); ownership and screening are deterministic (`analytics.py:210-363`); decimals are used in the model (`models.py:36-61`). | Attribution roles, explicit order, coverage/reason builder, document lineage, and view contracts. |
| Persistence | File/GCS CAS and retry loop already exist (`store.py:19-49`, `store.py:88-97`); report/review writes are immutable by hash/version (`main.py:303-345`). | Candidate assessments, follow-up/intake/history/Q&A artifacts and a global operation ledger. |
| Frontend shell | One React app already owns case/run/report/review and resets stale state when runs start (`frontend/src/main.tsx:21-47`, `127-170`). | Ten destinations, shared scoped selection, typed tables/cards, responsive states and new API methods. |
| Report safety | Synthesis citation membership and digit-free prose are validated (`investigation.py:87-102`); report JSON download exists (`investigation-report.tsx:34-43`). | Deterministic Q&A routing, semantic-support evaluation, canonical HTML/PDF model, escaping and parity. |

The current model allows only `source_kind: "synthetic"` for records/evidence
(`models.py:18-22`, `135-147`), so the requested provenance taxonomy is an
additive compatibility change. Existing evidence IDs must remain stable for old
reports. The current analytics helper sorts and deduplicates every `refs` list
(`analytics.py:9-30`); a path cannot recover traversal order from those refs.

# Reuse does not remove the critical work

The central attribution problem is real. Flow payloads contain account and amount
arrays but not ordered transaction IDs (`analytics.py:64-70`), while activity
evidence identifies one target but references the full baseline (`analytics.py:166-194`).
Inventory/truncation evidence can reference many records without flagging them.
Phase 1 therefore needs a pure reason builder with subject, participant and
context roles, coverage states and legacy unknown-order handling; this is new
backend behavior, not presentation-only work.

Pinned compatibility is also an explicit contract. `pinned_case` reconstructs
and rehashes the stored manifest (`main.py:96-108`), and existing tests prove a
run remains on the old snapshot after the current case changes
(`tests/test_reliability.py:58-103`). New reasons, explorers, intake children
and exports must preserve that behavior and never rewrite v1 report hashes.

Graph work is partly reusable but requires lineage. The current graph renders raw
records and formats money through `Number` (`frontend/src/flow-graph.tsx:4-29`);
document cross-comparison stores values but loses each value's page/anchor
lineage (`analytics.py:432-446`). Ordered money trails, overlap/depth labels and
per-field document locators therefore need backend and UI changes.

Q&A and export work has little existing runtime to wrap. There is no question
route, only the report route (`main.py:303-317`), and the frontend API has broad
index-signature record types plus one generic JSON helper (`frontend/src/api.ts:1-22`).
ReportLab is pinned (`pyproject.toml:9-16`), which removes dependency acquisition
work but not canonical model design, scope checks, idempotency, escaping, PDF
layout, parity tests or UI states.

# Vertical slices and critical path

| Slice | Scope and exit evidence | Human effort | Dependency |
|---|---|---:|---|
| V0 contracts/reasons | Additive schemas, attribution/order/coverage, reason builder, legacy fixtures and deterministic controls | 24–32h | — |
| V1 source workspace | Source/watchlist/finding/reason routes, candidate CAS records, shared inspector and cards | 24–32h | V0 |
| V2 continuity | Follow-up, auth boundary, restricted CSV/PDF/structured intake, quarantine, child snapshot and history recovery | 44–60h | V0; can run beside V1 |
| V3 explorers | Money order/path controls, ownership derivation/overlap, document field lineage and responsive UI | 28–40h | V1 |
| V4 Q&A/exports | Bounded retrieval, deterministic reason routing, immutable Q&A, canonical JSON/HTML/PDF parity | 36–48h | V1 + V2 |
| V5 offline release gate | Offline evaluator, seeded browser server/specs, all-five-scenario matrix, privacy/docs bundle | 24–36h | V3 + V4 |

The longest dependency chain is V0→V2→V4→V5: `128–176` human hours. The
explorer branch V0→V1→V3→V5 is `100–140` hours, so adding builders cannot
compress the continuity/Q&A chain below its serial work without splitting those
boundaries and assigning an integration owner. The plan’s date math is therefore
an aggregate-capacity calculation; it is not evidence that six to nine builders
can finish by the freeze.

# Evaluator and non-billable boundaries

The evaluator exposes `--split all|development|held-out`, `--live`,
`--repeats 1..3` and `--concurrency 1..3` (`evaluation/run-evaluation.py:192-197`).
Its current non-live path is not actually offline: it reads cloud config and
constructs `Cloud` before branching (`run-evaluation.py:70-74`), calls
`cloud.load_case` unconditionally (`:98-104`), and calls `cloud.extract` in the
non-live branch (`:122-131`). The current frontend has only a generic live
`test:e2e` command (`frontend/package.json:6-10`). These are concrete Phase 6
refactors, not merely documentation.

The non-billable boundary should be: current unit/API tests, deterministic
analytics, seeded offline server/browser flows, offline evaluator, typecheck,
build, escaping/parity tests, static secret/config review and docs. Provider
model calls, Document AI, live browser tests, OAuth setup, deploy/smoke/logging
and publication stay explicit later gates. Existing focused gates pass locally:
13 Python tests, TypeScript typecheck and Vite build; they cover only current
behavior, not any proposed route or feature.

# Uncertainties and assumptions

- Estimates assume one service, existing React/TypeScript conventions, pinned
  dependencies and synthetic fixtures; they exclude cloud setup, live provider
  evaluation and publication.
- Continuity is the lowest-confidence range because verified Google identity,
  allowlist, signed sessions, PDF parsing, quarantine and crash recovery are all
  new surfaces; no OAuth configuration currently exists (`phase-04:16-33`).
- Q&A/export effort assumes bounded in-request execution and one canonical view
  model; semantic answer quality still needs human evaluation (`phase-05:1-33`).
- No lower range is justified until V0 contracts are implemented and V1/V2 are
  decomposed into reviewable tasks with measured cycle time.
- The report does not assess cloud API version changes or live auth behavior;
  those remain explicit integration gates.

Status: DONE
Summary: Existing code materially reduces source, deterministic analytics, CAS, pinned-run and report plumbing, but all ten groups still require substantial new contracts, persistence, UI and offline-gate work. The 180–248h and six-to-nine-builder figures have correct arithmetic and a concrete phase map, yet are capacity planning bands rather than validated forecasts.
Concerns/Blockers: The V0→V2→V4→V5 critical path is 128–176 human-hours; shared-file serialization, missing OAuth setup and the evaluator’s current cloud access make deadline completion high risk even with the stated aggregate builder count.
