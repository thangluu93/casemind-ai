# Investigator workspace final code review

Reviewed 2026-10-11 against the accepted six-phase plan in
`plans/261010-2218-investigator-workspace-replan/`, the owning architecture,
data and evaluation documents, and the delegated backend/frontend/verification
scope. The review covered the final integrated source after the recovery,
identity, export, authentication, Q&A and 50-page PDF fixes landed.

## Scope and evidence

- Source: `backend/casemind/*.py`, `frontend/src/*`, the offline evaluator and
  workspace browser harness.
- Tests: `tests/*.py`, including the final route-permutation, 50-page provider,
  operation-recovery and Q&A citation cases, plus
  `frontend/e2e/workspace-offline.spec.ts` by inspection.
- Review posture: specification compliance first, followed by critical and
  informational API/web checks. The review explicitly traced source exposure,
  authentication and authorization, provider fencing, replay/idempotency,
  bounded intake, exact facts, unsupported Q&A, evidence/snapshot identity and
  legacy compatibility.
- Git metadata was unavailable in this filesystem workspace, so the review used
  the explicitly delegated file set rather than a Git diff.

## Overall assessment

No open critical, high or medium offline code defect remains in the reviewed
scope. The six issues found in the first pass were corrected and re-read in the
integrated source. Two regressions exposed by final acceptance tests—an intake
audit conflict for equivalent permutations and the stale 20-page parser/ledger
limit—were also corrected before this report.

Pre-landing result: **0 open findings; 8 verified resolved findings.** The local
implementation can proceed to the controller's full offline gate. It must not be
called release-ready until the accepted live GIS, GCS, Document AI, Gemini and
deployed-browser gates run with separate authorization.

## Open findings

None in the reviewed offline source and tests.

## Resolved finding dispositions

| Prior severity | Finding | Final disposition and evidence |
|---|---|---|
| High | Ordinary investigations lacked provider fencing and crash authority | Resolved in `backend/casemind/main.py:209-283`: request authority and quota projection precede execution; a 120-second `ExecutionContext` crosses Cloud and investigation boundaries; stale terminal writes fail. `tests/test_run_recovery.py` proves request/quota-gap reconstruction without provider replay and proves a changed fence blocks investigation. |
| High | Complete OCR text flowed into reports and exports | Resolved in `backend/casemind/analytics.py:384-400` with an extraction-evidence allowlist. `backend/casemind/exports.py:46-62` builds HTML/PDF from allowlisted report data and removes legacy evidence payload `text`; immutable legacy JSON report bytes remain unchanged. |
| High | Google login verification had no attempt bound | Resolved in `backend/casemind/workspace_routes.py:247-271` with atomic 60/global/minute and 6/session/minute limits before verification. `backend/casemind/auth.py:18-48` caps identity HTTP calls at five seconds and rejects malformed production credentials over 8 KiB before verification. |
| Medium | Generic deterministic counts, totals and percentages were uncited | Resolved in `backend/casemind/case_qa.py:60-165`: every exact fact includes pinned record or inventory references, relevant report evidence IDs are retained, large collections carry count/hash/scope, and unsupported filters abstain. `frontend/src/case-qa.tsx` and `source-explorer.tsx` make both record and inventory citations navigable. |
| Medium | Inline record ordering changed child identity | Resolved in `backend/casemind/workspace_routes.py:369-398` through canonical structured bytes and semantic record locators. `backend/casemind/intake.py:222-269` canonicalizes identity and audit records. The real-route permutation test now produces one child snapshot for reversed input order. |
| Medium | Operation recovery discarded the cursor after the first 100 keys | Resolved in `backend/casemind/workspace_routes.py:496-522`: the owner-scoped cursor is persisted and missing ordinary-run metadata is reconstructed without provider replay. `tests/test_run_recovery.py` places the target operation after the first page and verifies recovery on the next pass. |
| Medium | Equivalent child commits conflicted in the immutable intake audit | Found by the final route-permutation test and resolved in `backend/casemind/intake.py:258-269`: the audit stores canonical records/quarantine and keys distinct audits by child snapshot plus canonical batch hash. |
| High | Accepted 50-page PDFs still failed the parser/ledger and synchronous provider limit | Found by the final actual-PDF test and resolved across `backend/casemind/document_rendering.py`, `store.py` and `cloud.py`. The parser and ledger accept 50 pages; Document AI uses selected-page batches of 15/15/15/5 with global page/anchor remapping, per-attempt quota reservation, fence checks and no partial cache on failure. |

## Acceptance status

- Phase 1 snapshot identity, original-byte integrity, 500/501/5,000 transaction
  boundaries, PDF isolation and actual-page reservations have focused coverage.
- Phases 2–3 workspace, watchlist, reasons, money trail, ownership and document
  projections retain pinned source/run scope and bounded display behavior.
- Phase 4 authenticated intake, follow-up, linked execution, semantic
  order-independent identity, owner-scoped history and non-replaying recovery are
  implemented. Ordinary and linked provider paths share the absolute fenced
  execution contract.
- Phase 5 JSON/HTML/PDF, unsupported-question abstention, deterministic exact
  facts, cited source inventories and one bounded synthesis path are implemented.
  Legacy JSON reports remain byte/hash compatible.
- Phase 6 owning documentation now describes the implemented workspace and
  separates local evidence from the remaining live gates. The earlier offline
  evaluator completed 50 cases with 45 TP, 0 FP, 0 FN and 0 errors in the
  template-label metric; that does not measure OCR or synthesis quality.

## Verification performed by this review

- Focused final Python gate covering Q&A, evidence foundation, route integration,
  recovery, exports and reliability: **47 passed**, one Starlette deprecation
  warning.
- New ordinary-run recovery/fence/cursor module: **3 passed**.
- Ruff over reviewed backend and test files: **passed**.
- Frontend TypeScript project check: **passed**.
- Earlier integration baseline before final fixes: **68 passed**; Ruff,
  frontend typecheck and frontend build passed.
- Offline evaluator, 50 generated cases: **45 TP, 0 FP, 0 FN, 0 errors**;
  source/citation membership checks passed.
- Browser E2E was not run by this reviewer because the deterministic port 8081
  belongs to the active root integration process. The reviewer did not stop or
  replace another session's process.
- Test coverage percentage was not measured; no coverage threshold is configured.

## Remaining release gates

These are accepted external validation gates, not unresolved offline defects:

1. Run the controller's full Python, lint, frontend build and fixed-port offline
   browser matrix after integration is quiescent.
2. With separate authorization, verify real GIS, GCS generation behavior,
   Document AI selected-page responses, Gemini synthesis/tool behavior and
   semantic answer support.
3. With separate deployment authorization, run authenticated deployed-browser,
   logs and rollback checks before describing the extension as released.

## Review limitations

- Live Google provider behavior, deployed identity configuration and deployed
  browser behavior were intentionally not exercised.
- Without Git metadata, the review could not identify unrelated changes outside
  the delegated source set.
