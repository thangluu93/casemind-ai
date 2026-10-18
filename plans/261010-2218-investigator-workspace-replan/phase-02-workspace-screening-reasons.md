---
phase: 2
title: "Workspace, screening and reasons"
status: completed
priority: P1
effort: "24-32 person-hours"
dependencies: [1]
---

# Phase 2: Workspace, screening and reasons

## Goal

Deliver Watchlist & Screening, Source explorer, typed Finding cards and deterministic transaction reasons against a visibly selected case or immutable run snapshot.

## Verified context

- Frontend state resets on case/run changes and reloads the pinned case with its report (`frontend/src/main.tsx:38-91,127-170`). Preserve this stale-result protection.
- `api.ts` uses broad index-signature records and one JSON helper (`frontend/src/api.ts:1-22`); add precise contracts without breaking existing report types.
- Screening emits potential, inconclusive and likely-false-positive states from supplied names/identifiers (`backend/casemind/analytics.py:314-363`). Empty input is not clearance.
- Current source routes return one record from current case or pinned run (`backend/casemind/main.py:110-119,166-175`). Run navigation must never fall back to current data.

## API and UI contracts

1. `GET /api/cases/{case_id}/workspace` and `GET /api/runs/{run_id}/workspace` return bounded typed inventory: scope/snapshot, counts, sources by type, screening candidates, finding summaries and coverage. Run scope requires ownership and manifest integrity.
2. `GET /api/runs/{run_id}/transactions/{transaction_id}/reasons` calls Phase 1’s pure builder. Case-only views may inspect sources but cannot claim completed-run reasons.
3. `POST /api/runs/{run_id}/screening-assessments` accepts candidate IDs, report hash/version, assessment, reason and idempotency key. It stores immutable CAS records under Phase 1 `ActorRef`/owner-alias resolution, independent of report disposition; a later claim maps authority without rewriting the assessment or old review.
4. UI scope is `{caseId, runId?, snapshotId, selectedSourceId?, selectedEvidenceId?, selectedTransactionId?}`. One inspector is reused across views. Responses commit only when their scope key still matches.
5. Finding renderers key on tool/version. Unknown versions show labeled raw payload. Deterministic payloads own numbers; model hypotheses stay labeled and digit-free.

## Files and ownership

| Action | Absolute path | Owner/change |
|---|---|---|
| Create | `/Users/thangluu/Repos/casemind-ai/backend/casemind/workspace.py` | Backend lane: inventory, typed findings and candidate assessments. |
| Modify | `/Users/thangluu/Repos/casemind-ai/backend/casemind/main.py` | Integration owner: additive workspace/reason/assessment routes. |
| Create | `/Users/thangluu/Repos/casemind-ai/tests/test_workspace_api.py` | Backend lane: scope, CAS, reason and compatibility tests. |
| Modify | `/Users/thangluu/Repos/casemind-ai/frontend/src/api.ts` | Integration owner: exact contracts/helpers. |
| Create | `/Users/thangluu/Repos/casemind-ai/frontend/src/source-explorer.tsx` | UI lane: typed tables, filters and inspector. |
| Create | `/Users/thangluu/Repos/casemind-ai/frontend/src/watchlist-screening.tsx` | UI lane: identity comparison and assessment. |
| Create | `/Users/thangluu/Repos/casemind-ai/frontend/src/finding-cards.tsx` | UI lane: cards, raw fallback, gaps and citations. |
| Create | `/Users/thangluu/Repos/casemind-ai/frontend/src/transaction-reasons.tsx` | UI lane: roles, order, rules, alternatives and gaps. |
| Modify | `/Users/thangluu/Repos/casemind-ai/frontend/src/evidence-review.tsx` | UI lane: shared inspector/cards. |
| Modify | `/Users/thangluu/Repos/casemind-ai/frontend/src/case-navigation.tsx` | UI lane: destinations and scope labels. |
| Modify | `/Users/thangluu/Repos/casemind-ai/frontend/src/main.tsx` | Integration owner: scoped reducer/composition. |
| Modify | `/Users/thangluu/Repos/casemind-ai/frontend/src/styles.css` | Integration owner: responsive states. |

Phase 2 and 4 may run after Phase 1 because their new files are disjoint. Only the integration owner edits shared files.

## Implementation steps

1. Define response models with scope, coverage, hidden count, Decimal strings, timestamps, classification/origin and stable IDs. Cap collections with truncation metadata.
2. Build workspace data strictly from resolved case or pinned run with no provider/model call. Preserve missing/conflicting fields.
3. Store candidate assessments by resolved ActorRef/run/candidate/idempotency, bound to report hash/version without mutating report review. Test assessment before sign-in, claim/rotation, relogin/replay and cross-owner denial.
4. Add a reducer that invalidates selected details on scope change and drops out-of-order responses.
5. Build accessible Sources/Watchlist views with disclosed filters and loading/empty/error/raw states.
6. Render typed findings while retaining all evidence IDs. Separate hypotheses, indicators, verification and human assessment.
7. Render reasons with role, ordered sources, actual parameters, coverage, alternatives and next checks. Distinguish no indicator from not evaluated.

## Verification

```bash
./.venv/bin/python -m pytest tests/test_workspace_api.py tests/test_analytics.py tests/test_store_api.py tests/test_reliability.py -q
./.venv/bin/python -m ruff check backend/casemind/workspace.py backend/casemind/main.py tests/test_workspace_api.py
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

Test same-name/conflicting identity, missing identity, empty list, CAS conflict, current versus pinned source, target versus baseline, unknown tool version, broken source, filter disclosure, stale response and keyboard selection.

## Risks and rollback

| Risk | Likelihood × impact | Mitigation |
|---|---|---|
| UI mixes current and pinned scope | High × High | Scope key on every response/selection. |
| Screening implies identity/criminality | Medium × High | Field states, supplied-list labels and separate human judgment. |
| Renderer drops evidence | Medium × High | Version registry, raw fallback and parity tests. |
| Shared edits collide | High × Medium | One integration owner serializes them. |

Rollback hides new routes/navigation and restores the backed-up shell. Immutable assessments remain inaccessible audit records.

## Done

- [x] Four feature groups work before/after a run with explicit scope.
- [x] Every fact/comparison resolves to a pinned source.
- [x] Candidate assessments are immutable and independent of report review.
- [x] Empty, failed, missing, conflicting, truncated and unknown states are visible.

## Execution evidence

Completed locally on 2026-10-11. See the [execution report](../reports/cook-261011-1326-investigator-workspace.md)
and [independent review](../reports/code-review-261011-workspace.md).
Provider behavior and deployed authentication remain Phase 6 live gates.
