# Phase 3: Investigation Workspace and Human Review

## Overview

- **Status:** Implemented; see delivery evidence
- **Priority:** P1
- **Effort:** 14h
- **Dependency:** Phase 2 API contract
- **Objective:** deliver a non-chat-first Vite React/TypeScript workspace that makes execution, evidence, uncertainty, graph facts, and immutable human decisions inspectable.

## Context and Invariants

- The required journey is case selection, execution timeline, directed graph, evidence inspection, structured report, and human disposition ([prototype experience](../../docs/prototype-brief.md#prototype-experience)).
- Provenance, claim kind, verification status, and synthetic labels must be visible ([data model](../../docs/data-model.md#provenance-and-verification-are-separate-axes)).
- Reviews reference an immutable report version/hash and persist separately from agent output ([core records](../../docs/data-model.md#core-records)).

## Data Flow

1. The browser loads the five-case inventory and source coverage from the API; it receives no ground truth or hidden scenario hints.
2. Starting a case sends an idempotency key. Timeline polling/streaming renders persisted plans, role/tool events, durations, evidence counts, gaps, limits, and provider failures.
3. Selecting a finding filters graph nodes/edges to cited evidence and opens the exact transaction row, relationship, screening attributes, or document page/field.
4. The report view separates observations, indicators, hypotheses, alternatives, unresolved questions, limitations, and transparent priority contributors.
5. Approve, reject, or request follow-up submits the selected report hash plus a required reason. Conflict or stale-version responses keep the user's draft reason and prompt an explicit refresh.

## Actual Files

- Controller/contract: `frontend/src/{main.tsx,api.ts}`.
- Views: `case-navigation.tsx`, `flow-graph.tsx`, `investigation-report.tsx`, `evidence-review.tsx`, `format-label.ts`, `styles.css` under `frontend/src/`.
- Browser verification: `frontend/e2e/investigation.spec.ts`, `frontend/playwright.config.ts`.

## Implementation Steps

1. Generate TypeScript DTOs from the stable API schema or keep a single checked contract source; reject unknown status/label values at the boundary.
2. Build a responsive investigation layout with persistent case/run context, accessible keyboard navigation, visible loading/error/reconnect states, and synthetic-data labels on cases, sources, evidence, and reports.
3. Render a directed typed graph for persons, legal entities, accounts, transfers, and ownership. Finding selection highlights only cited edges; missing percentages and conflicting identities remain visually unresolved.
4. Render event timing and tool provenance without chain-of-thought. Show truncation, retries, provider failures, token/page/query usage, spend-pause state, and `completed_with_gaps` prominently.
5. Resolve evidence through scoped API URLs; show original locators, derivation parameters, hashes, verification status, and document page/field anchors.
6. Require a reason for every review action and bind the request to the displayed report version/hash. Disable review controls while a run is incomplete or when the version is stale.
7. Add component tests and a five-scenario browser test covering run/reconnect, graph-to-source navigation, review persistence, concurrent version conflict, and accessibility-critical controls.

## Validation

Use the prepared Python environment. Live evaluation consumes the persistent allowance; do not rerun merely to repeat a passing check.

```bash
npm --prefix frontend run typecheck
npm --prefix frontend run build
CASEMIND_TEST_URL=https://casemind-ai-q36bubsb3a-as.a.run.app npm --prefix frontend exec -- playwright test --config=frontend/playwright.config.ts
```

Measured results, actual files, remaining gates and rollback route: [delivery evidence](../reports/261009-prototype-delivery.md). Original planned fixture/module splits were consolidated into the current source files; the source tree is authoritative.

## Risks and Mitigations

| Risk | Likelihood × impact | Mitigation |
|---|---|---|
| Graph looks persuasive beyond evidence | Medium × High | Render only typed source-backed edges; finding selection narrows to citations; show unknown/conflicting state. |
| Reconnect duplicates a run | Medium × High | Persist and reuse idempotency key; reload saved events instead of auto-starting. |
| Review overwrites a newer report | Medium × Critical | Version/hash precondition and visible conflict response. |
| UI leaks truth or credentials | Low × Critical | Contract/build scans; server-mediated evidence; no provider config in frontend env. |

## Rollback

Redeploy the previous frontend bundle while keeping backend reports and reviews. A UI rollback must not delete or rewrite persisted decisions; incompatible API versions block the deploy gate.

## Todo

- [x] Build case, timeline, graph, evidence, report, and usage views
- [x] Implement version-bound review workflow
- [x] Verify build, responsive rendering, reconnect and live five-scenario E2E; dedicated component/automated accessibility suites remain unimplemented
