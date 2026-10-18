---
phase: 2
title: "Sources, watchlist, finding cards and reasons UI"
status: pending
priority: P0
effort: "24-32 person-hours"
dependencies: [1]
---

# Phase 2: Sources, watchlist, finding cards and reasons UI

## Goal

Make source inventory, screening evidence, readable findings, and “Why this
transaction was flagged” available through one case/run-scoped selection model.

## Context and verified foundations

- Case and pinned-run source routes already exist
  (`backend/casemind/main.py:110`, `backend/casemind/main.py:166`).
- The frontend stores one selected evidence/source and otherwise renders payload
  JSON (`frontend/src/main.tsx:21`, `frontend/src/evidence-review.tsx:90`).
- The current graph chooses raw records directly and formats money through
  JavaScript `Number` (`frontend/src/flow-graph.tsx:16`), which is unsuitable for
  exact financial display.
- Existing screening compares names and shared identifiers without merging
  identities (`backend/casemind/analytics.py:314`).

## Requirements

- [ ] Sources are accessible before a run and pinned to the run snapshot after a
      run. Every view visibly states current-input versus immutable-run scope.
- [ ] Provide typed tables for transactions, entities, accounts, relationships,
      documents and supplied watchlist records with search/filter/sort, coverage
      counts, stable IDs, explicit missing values and raw JSON as a secondary view.
- [ ] Keep Sanctions and PEP distinct. Name similarity is a comparison, never an
      identity or crime probability. Missing identifiers never count as matches.
- [ ] Candidate human assessments are immutable records independent of report
      disposition and bound to candidate/evidence/snapshot identity.
- [ ] Finding cards keep observation/indicator/hypothesis, verification state,
      facts, citations, limitations, alternatives and next checks distinct.
- [ ] Transaction reasons expose assessment, tool/version/rule parameters, actual
      values, role, coverage, sources, alternatives, limitations and next checks.
- [ ] Empty, missing, failed, unsupported-version and truncated states remain
      visible. Unknown renderers fall back to labeled raw evidence.

## Data flow

1. The workspace loads a current case inventory or a pinned run snapshot.
2. Shared selection state carries `{scope, caseId, runId?, sourceId?, evidenceId?}`.
3. Source/watchlist/finding/graph selections open one typed source inspector.
4. The transaction-reason route calls the phase-1 pure builder against the owned
   pinned run, then the UI renders deterministic facts without another model call.
5. Candidate assessment POST validates the owned run, snapshot hash and candidate
   evidence, then writes once with CAS; retry of the same idempotency key returns
   the same object and a different assessment conflicts.

## Files to modify or create

| Action | Absolute path | Change |
|---|---|---|
| Modify | `/Users/thangluu/Repos/casemind-ai/backend/casemind/models.py` | Add candidate-assessment request/response contracts. |
| Modify | `/Users/thangluu/Repos/casemind-ai/backend/casemind/main.py` | Add proposed owned reason and candidate-assessment routes; reuse pinned source checks. |
| Modify | `/Users/thangluu/Repos/casemind-ai/frontend/src/api.ts` | Add precise source, finding, reason and assessment types/methods. |
| Modify | `/Users/thangluu/Repos/casemind-ai/frontend/src/main.tsx` | Compose destination navigation and shared scoped selection state. |
| Modify | `/Users/thangluu/Repos/casemind-ai/frontend/src/case-navigation.tsx` | Add Overview/Sources/Watchlist/Findings destinations and scope label. |
| Create | `/Users/thangluu/Repos/casemind-ai/frontend/src/source-explorer.tsx` | Typed source tables and filters. |
| Create | `/Users/thangluu/Repos/casemind-ai/frontend/src/source-inspector.tsx` | Shared source/evidence/raw inspector. |
| Create | `/Users/thangluu/Repos/casemind-ai/frontend/src/watchlist-screening.tsx` | Screening comparisons and immutable assessment form/history. |
| Create | `/Users/thangluu/Repos/casemind-ai/frontend/src/finding-cards.tsx` | Tool-specific cards with safe unknown-version fallback. |
| Create | `/Users/thangluu/Repos/casemind-ai/frontend/src/transaction-reasons.tsx` | Exact fact/role/order/coverage presentation. |
| Modify | `/Users/thangluu/Repos/casemind-ai/frontend/src/evidence-review.tsx` | Delegate details to the shared inspector and retain report review. |
| Modify | `/Users/thangluu/Repos/casemind-ai/frontend/src/styles.css` | Accessible tables, cards, drawers and responsive states in the accepted visual direction. |
| Modify | `/Users/thangluu/Repos/casemind-ai/tests/test_store_api.py` | Route scope, idempotency, immutability and cross-session denial. |
| Create | `/Users/thangluu/Repos/casemind-ai/tests/test_workspace_views.py` | API view-contract tests using stored pinned fixtures. |

Routes proposed by this phase do not exist yet:
`GET /api/runs/{run_id}/transactions/{transaction_id}/reasons`,
`GET /api/runs/{run_id}/screening-assessments`, and
`POST /api/runs/{run_id}/screening-assessments`.

## Implementation steps

1. Add the reason route behind `owned_run`/`pinned_case`; reject transactions not
   in the selected snapshot and return phase-1 coverage states without model use.
2. Add immutable candidate assessment storage keyed by run, candidate pair and
   generated assessment ID. Bind records to evidence IDs, snapshot hash, reviewer
   session owner, reason and timestamp; never mutate `reviews/{run}/1`.
3. Replace broad frontend index signatures for known records with discriminated
   types. Keep a raw fallback for unknown evidence versions.
4. Implement shared selection/scope state so current-case links never replace a
   pinned-run source after report selection. Clear stale findings immediately when
   a new run starts or fails.
5. Build Sources, Watchlist, Finding cards and Transaction reasons. Format decimal
   strings directly, preserve currency, show UTC source timestamps plus labeled
   locale display, and disclose active filters/hidden row counts.
6. Ensure all tables, drawers, cards and source links work by keyboard and expose
   loading, empty, error, missing and unsupported states.

## Verification gates

```bash
./.venv/bin/python -m pytest tests/test_explanations.py tests/test_store_api.py tests/test_workspace_views.py -q
./.venv/bin/python -m ruff check backend/casemind/models.py backend/casemind/main.py tests/test_store_api.py tests/test_workspace_views.py
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

The existing `npm --prefix frontend run test:e2e` starts live investigations in
`frontend/e2e/investigation.spec.ts:4`; treat it as billed/live and do not use it
as this phase's offline gate.

## Success criteria

- [ ] Source counts and records match current or pinned snapshots without scope drift.
- [ ] Screening comparisons show conflicts/missing fields and preserve category.
- [ ] Candidate assessment retries are idempotent and prior decisions immutable.
- [ ] Every finding/reason fact opens its source; no baseline row inherits suspicion.
- [ ] Reopening cards or reasons makes no model/provider call.

## Risks and rollback

| Risk | Likelihood × impact | Mitigation |
|---|---|---|
| Shared selection shows stale run evidence | Medium × High | Include scope/run identity in state and reset atomically on case/run transitions. |
| Tool-specific renderer drifts from payload | Medium × High | Version dispatch plus fixture tests and raw fallback. |
| Assessment conflicts with report review | Low × High | Separate keyspace/models and immutable CAS writes. |

Rollback by removing the new destinations/routes while retaining additive
assessment artifacts. Existing graph, evidence ledger, review and JSON export
continue to use the old contracts.

## Todo

- [ ] Add scoped routes and immutable candidate assessments.
- [ ] Build shared inspector, sources, screening, cards and reason panel.
- [ ] Pass API, typecheck, build and accessibility-state checks.
