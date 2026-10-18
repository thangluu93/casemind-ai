# Phase 2: Deterministic Investigation and ADK Runtime

## Overview

- **Status:** Implemented; see delivery evidence
- **Priority:** P1
- **Effort:** 20h
- **Dependency:** Phase 1 contracts and provider smoke checks
- **Objective:** execute real deterministic analytics through four bounded ADK specialists and an orchestrator, then persist only citation-valid immutable reports.

## Context and Invariants

- Role tool allowlists and boundaries are defined in [agent responsibilities](../../docs/system-architecture.md#agent-responsibilities).
- Workflow ordering, one repair pass, immutable reports, and human-only disposition are defined in [the investigation workflow](../../docs/system-architecture.md#investigation-workflow).
- Path, cycle, structuring, ownership, screening, and document conclusions must retain limitations in [tools and risk interpretation](../../docs/system-architecture.md#tools-and-risk-interpretation).

## Data Flow

1. `main.py` resolves a case and idempotency key to a pinned input manifest, then streams persisted run events.
2. `investigation.py` asks the orchestrator for a structured plan, validates specialist coverage and tool allowlists, and dispatches Transaction, Entity, Compliance, and Document roles with bounded concurrency.
3. Every role calls functions in `analytics.py` or the Phase 1 cloud interfaces. Tool outputs include original record locators, parameters, versions, caps, and truncation.
4. Evidence validation rejects wrong-scope, unresolved, fabricated, or numerically inconsistent claims. Gemini may synthesize explanations and alternatives from validated evidence only.
5. One bounded repair pass may fix citation shape. The service persists `completed_with_gaps` or failure when support is still missing; it never inserts canned model output.
6. A validated report version and usage totals are appended to Cloud Storage. The run stops at `awaiting_review`; no agent can invoke the review-write route.

## Actual Files

- Runtime: `backend/casemind/{analytics,investigation,main,priority}.py` plus shared cloud/store contracts.
- Checks: `tests/{test_analytics,test_investigation,test_store_api,test_reliability}.py`, `scripts/smoke-cloud.py`.
- Related primitives are grouped into four specialist tool entry points; evidence retains operation names and parameters.

## Implementation Steps

1. Implement deterministic `get_transactions`, `trace_flows`, `detect_cycles`, `detect_structuring`, `summarize_activity`, `resolve_candidates`, `get_relationships`, `trace_ownership`, `screen_candidates`, `compare_identifiers`, `get_watchlist_record`, `extract_document`, `normalize_fields`, and `compare_fields` operations.
2. Enforce directed/time-respecting path and cycle rules, decimal amounts, explicit currency boundaries, depth/window/result caps, known-percentage ownership arithmetic, candidate rather than automatic fuzzy identity merges, and unresolved low-confidence fields.
3. Define five ADK roles inside one process: orchestrator plus four specialists. Give each the minimum tools from the architecture and typed structured outputs requiring evidence IDs, limitations, missing data, and alternatives.
4. Enforce one active run per session, no more than 20 tool calls, two attempts only for transient provider failures, per-step timeouts, a 120-second hard deadline, token/page/query budgets, and no unmanaged background work.
5. Expose case inventory, start run, event stream/read, evidence read, immutable report read, and version-bound review endpoints. Review writes use application code outside agent tool registration.
6. Validate evidence membership, source locators, numeric recomputation, report coverage, synthetic/source labels, and indicator-based priority before completion.
7. Test altered amounts, reversed/reordered edges, mixed currencies, cycles/controls, missing ownership, duplicate names, provider timeouts, malformed extraction, prompt injection, idempotent retries, and stale-run interruption.

## Validation

Use the prepared Python environment. Live evaluation consumes the persistent allowance; do not rerun merely to repeat a passing check.

```bash
python -m pytest tests/test_analytics.py tests/test_investigation.py tests/test_reliability.py -q
CASEMIND_USE_GCLOUD=true python scripts/smoke-cloud.py
```

Measured results, actual files, remaining gates and rollback route: [delivery evidence](../reports/261009-prototype-delivery.md). Original planned fixture/module splits were consolidated into the current source files; the source tree is authoritative.

## Risks and Mitigations

| Risk | Likelihood × impact | Mitigation |
|---|---|---|
| ADK behavior/version blocks the slice | Medium × High | Keep contracts and tools framework-neutral; use the direct Google SDK bounded loop only if the same five role/tool boundaries remain observable. |
| Model invents evidence or arithmetic | High × Critical | Resolve and recompute every factual claim; one repair pass, then fail visibly. |
| Request exceeds Cloud Run deadline | Medium × High | Small preloaded cases, parallel independent specialists, hard caps, explicit gaps; add no background worker in this scope. |
| Similar names create false identity edges | Medium × Critical | Candidates stay separate; exact verified identifiers or human review are required for a graph merge. |

## Rollback

Disable the run-start endpoint and redeploy the Phase 1-compatible revision. Keep generated inputs and immutable run artifacts for diagnosis; mark interrupted runs rather than rewriting them.

## Todo

- [x] Implement and prove deterministic tools
- [x] Integrate five bounded ADK roles with live Gemini
- [x] Add evidence/report validation and API routes
- [ ] Complete exhaustive prompt-injection and blocking-RPC deadline fault proof (focused tests and live retries pass)
