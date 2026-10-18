---
phase: 5
title: "Case Q&A and exports"
status: completed
priority: P1
effort: "36-48 person-hours"
dependencies: [2, 4]
---

# Phase 5: Case Q&A and exports

## Goal

Add bounded cited case Q&A plus printable HTML and generated PDF exports without changing the existing sole JSON report export, its bytes, hashes or review semantics.

## Verified context

- Synthesis validation rejects out-of-run citations and digits in model prose (`backend/casemind/investigation.py:87-102`). Q&A retains both boundaries.
- The runner has model/tool/token bounds and throttling (`backend/casemind/investigation.py:39-84,124-184`) but is nested and needs a reusable adapter after Phase 4.
- `/api/runs/{run_id}/report` returns the stored object directly and UI downloads it (`backend/casemind/main.py:303-309`; `frontend/src/investigation-report.tsx:34-43`). That route/serialization remains unchanged.
- ReportLab is pinned (`pyproject.toml:9-16`). The two new readable formats can share one internal view model while existing JSON remains authoritative.

## Q&A and export contracts

1. `POST /api/runs/{run_id}/questions` accepts question, idempotency key and expected report hash. Its canonical request hash binds resolved owner, `question` operation type, key, parent snapshot, report hash/version, sorted retrieval source-hash set and normalized question. Equal hash returns the operation; unequal key reuse returns 409 before quota.
2. Retrieval loads the owned run, exact report/review/snapshot, then caps evidence/source count and serialized bytes. No SQL, URL fetch, cross-case search, implicit run, mutation or disposition.
3. Transaction/exact-number questions bypass the model. Other families reserve a Q&A operation, call one bounded synthesis under shared quotas/deadline, validate digit-free prose/citations/shape/abstention and store immutable success/failure.
4. Citation membership is mechanical; Phase 6 separately grades semantic support.
5. `ExportView` is an internal projection from pinned report/evidence/review plus allowlisted excerpts/locators. Keep `/report` as the sole JSON export; add only `GET /api/runs/{run_id}/exports/report.html` and `.pdf`.
6. HTML is self-contained, escaped, semantic and script-free. PDF treats untrusted content as text. HTML and PDF render the same versioned `ExportView`. Their common report facts, IDs and hashes must match the existing JSON; additional reason, coverage, excerpt and review sections trace explicitly to pinned evidence/review IDs, hashes and versions rather than being claimed as fields already present in legacy JSON.

## Files and ownership

| Action | Absolute path | Owner/change |
|---|---|---|
| Modify | `/Users/thangluu/Repos/casemind-ai/backend/casemind/models.py` | Integration owner: Q&A/export schemas. |
| Modify | `/Users/thangluu/Repos/casemind-ai/backend/casemind/investigation.py` | Q&A backend: reusable bounded runner with no widened tools. |
| Create | `/Users/thangluu/Repos/casemind-ai/backend/casemind/case_qa.py` | Q&A backend: classification/retrieval/routing/artifacts. |
| Create | `/Users/thangluu/Repos/casemind-ai/backend/casemind/exports.py` | Export backend: canonical model/renderers. |
| Modify | `/Users/thangluu/Repos/casemind-ai/backend/casemind/main.py` | Integration owner: additive routes/headers. |
| Create | `/Users/thangluu/Repos/casemind-ai/tests/test_case_qa.py` | Q&A lane: scope/abstention/bounds/idempotency/adversarial. |
| Create | `/Users/thangluu/Repos/casemind-ai/tests/test_exports.py` | Export lane: HTML/PDF parity to existing report JSON, escaping, exact values and legacy bytes. |
| Modify | `/Users/thangluu/Repos/casemind-ai/tests/test_investigation.py` | Runner and numeric-prose regression. |
| Modify | `/Users/thangluu/Repos/casemind-ai/frontend/src/api.ts` | Integration owner: Q&A/export/download contracts. |
| Create | `/Users/thangluu/Repos/casemind-ai/frontend/src/case-qa.tsx` | UI lane: cited history, abstention, quota/failures. |
| Modify | `/Users/thangluu/Repos/casemind-ai/frontend/src/investigation-report.tsx` | UI lane: existing JSON plus printable HTML and generated PDF controls. |
| Modify | `/Users/thangluu/Repos/casemind-ai/frontend/src/main.tsx` | Integration owner: Q&A composition. |
| Modify | `/Users/thangluu/Repos/casemind-ai/frontend/src/styles.css` | Integration owner: Q&A/print presentation. |

Phase 5 starts after Phase 4 releases `investigation.py` and operation ledger. One integration owner serializes shared files.

## Implementation steps

1. Extract the smallest model adapter with injected instruction/schema, no tools by default, one-call cap, shared deadline/throttle and usage accounting.
2. Implement strict classification/retrieval allowlists. Deterministically detectable unsupported requests abstain before provider reservation.
3. Route exact values/reasons to deterministic builders. Model context carries selected interpretations and stable fact refs; numeric values remain separate fields.
4. Use Phase 4 request-envelope/manifest/events and `reserving→ready→executing→terminal` states. Project quota/history idempotently before `ready`; provider starts only from confirmed `ready`. Persist retrieval IDs/usage/answer or sanitized failure; recovery repairs projections or marks interruption without retry.
5. Build a stable ordered internal `ExportView` from semantic IDs and pinned artifacts with excerpts or explicit offline limitation; never infer meaning from legacy report list order, reorder stored reports, or make authenticated URLs the sole evidence path.
6. Leave JSON serialization/route untouched. Escape HTML by context and render PDF with ReportLab text/table/page primitives from the same `ExportView`. Check HTML/PDF field parity, compare common facts/IDs/hashes to existing JSON, and validate every extra section against its pinned evidence/review identity and version.
7. Add safe filenames, content disposition, media types, `nosniff`, UI history/citation navigation and explicit format controls.

## Verification

```bash
./.venv/bin/python -m pytest tests/test_case_qa.py tests/test_exports.py tests/test_investigation.py tests/test_store_api.py tests/test_reliability.py -q
./.venv/bin/python -m ruff check backend/casemind/case_qa.py backend/casemind/exports.py backend/casemind/investigation.py backend/casemind/main.py tests
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

Test prompt/document injection, cross-run IDs, unsupported family, contradictions, exact values, digit rejection, same-key changed question/report/retrieval hashes returning 409 with zero quota, concurrent duplicates, crash-boundary recovery, HTML scripts/URLs, PDF controls, format parity, offline limitation and legacy `/report` bytes.

## Risks and rollback

| Risk | Likelihood × impact | Mitigation |
|---|---|---|
| Persuasive unsupported answer | High × High | Bounded retrieval, abstention, validation and semantic grading. |
| Q&A bypasses quota/recovery | Medium × High | Shared Phase 4 ledger and contention tests. |
| Export injection/scope leak | Medium × High | Allowlist, escaping, owner checks, no session URLs. |
| Format drift | Medium × Medium | One view model and parity fixtures. |

Rollback disables new routes/UI independently; legacy JSON stays. Immutable Q&A/export artifacts remain audit records.

## Done

- [x] Q&A cannot widen scope/tools and abstains correctly.
- [x] Model prose is digit-free; exact values/reasons are deterministic.
- [x] Duplicate/quota/restart behavior uses shared operations.
- [x] HTML/PDF agree through one ExportView; common JSON facts/IDs/hashes match, extra sections resolve to pinned evidence/review versions, and JSON route/bytes remain unchanged.

## Execution evidence

Completed locally on 2026-10-11. See the [execution report](../reports/cook-261011-1326-investigator-workspace.md)
and [independent review](../reports/code-review-261011-workspace.md).
Provider behavior and deployed authentication remain Phase 6 live gates.
