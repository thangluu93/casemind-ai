# Phase 1: Foundation, Contracts, and Cloud Feasibility

## Overview

- **Status:** Implemented; see delivery evidence
- **Priority:** P1
- **Effort:** 14h
- **Dependency:** None
- **Objective:** establish the Python/Vite project, typed evidence contracts, seeded five-scenario data, durable adapters, cost controls, and real Google Cloud smoke checks before agent behavior is built.

## Context and Invariants

- Stable namespaced identifiers, provenance, monetary precision, and evaluator-only `GroundTruth` are required by [the data model](../../docs/data-model.md#core-records).
- The deployment boundary is one service with BigQuery snapshots, Cloud Storage artifacts, server-side Gemini and Document AI calls ([system architecture](../../docs/system-architecture.md#system-boundary)).
- The public demo accepts preloaded synthetic cases only and must reject uploads, external URLs, cross-case access, and document instructions that widen scope ([system architecture](../../docs/system-architecture.md#prototype-security-and-operational-route)).

## Data Flow

1. A versioned seed enters `generator.py`; it produces visibly synthetic entities, accounts, relationships, transactions, documents, and watchlist records.
2. Runtime inputs and evaluator truth are written to separate roots with separate access paths. Only the evaluation runner can load truth.
3. `models.py` validates IDs, enums, decimal money, timestamps, provenance, source locators, report/review version bindings, and usage records.
4. `cloud.py` uploads immutable snapshot tables to BigQuery and documents/manifests to Cloud Storage. `store.py` reads or appends case/run artifacts with generation-match preconditions.
5. The verified global Vertex `gemini-3.1-flash-lite` call establishes model access. Remaining live smoke calls verify structured tool output, one Document AI extraction from a watermarked synthetic form, one bounded BigQuery query, and one conditional Storage write before their exact versions/regions are pinned.

## Actual Files

- Contracts/adapters: `pyproject.toml`, `backend/casemind/{models,generator,cloud,store}.py`.
- Checks: `tests/test_contracts.py`, `tests/test_store_api.py`, `scripts/{setup-cloud,configure-runtime,check-cost-controls}.py`.
- Frontend foundation: package/lock/TypeScript/Vite configuration and `frontend/index.html`.
- Packaging exclusions: `.gitignore`, `.dockerignore`, `.gcloudignore`; no credential examples needed.

## Implementation Steps

1. Reuse `.venv` with verified Google ADK `2.11.0` and `gemini-3.1-flash-lite`; select compatible FastAPI, Pydantic, Vertex AI/Gen AI, Document AI, BigQuery, Storage, and pytest releases, then pin the full set after the remaining live smoke checks pass.
2. Implement all core records and cross-record validators. Reject float money, unresolved evidence IDs, wrong-case references, overwrite of approved reports, and review hashes that do not match the selected report.
3. Generate five representative demo cases plus the 50-case benchmark: five positive and five control variants per scenario, split by seed/identity/topology into 20 development and 30 held-out cases. Write runtime bundles and truth outside one another.
4. Generate watermarked synthetic KYC/KYB PDFs and a fictional watchlist. Store hashes, generator version, seed, source kind, and usage approval in manifests.
5. Implement local adapters and Google adapters behind the same typed interfaces. BigQuery templates must use parameters, partition filters, row caps, dry runs, and maximum bytes billed; Storage writes must compare generations.
6. Check project `251896792352`, resolve its project ID, verify APIs/IAM/regions, and confirm the two existing VND monthly project-filtered budgets: `750,000 VND` at 50/80/100% and `950,000 VND` at 80/100%, both excluding all credits as gross service spend. Record verification output and never treat alerts as hard caps.
7. Persist global/session usage counters and enforce initial ceilings of 200 model-backed runs, 50,000 input tokens and 8,000 output tokens per run, plus configured document pages and BigQuery bytes. Completed artifacts stay readable when new runs are paused.

## Validation

Use the prepared Python environment. Live evaluation consumes the persistent allowance; do not rerun merely to repeat a passing check.

```bash
python -m pytest tests/test_contracts.py tests/test_store_api.py -q
CASEMIND_USE_GCLOUD=true python scripts/setup-cloud.py
CASEMIND_USE_GCLOUD=true python scripts/check-cost-controls.py
```

Measured results, actual files, remaining gates and rollback route: [delivery evidence](../reports/261009-prototype-delivery.md). Original planned fixture/module splits were consolidated into the current source files; the source tree is authoritative.

## Risks and Mitigations

| Risk | Likelihood × impact | Mitigation |
|---|---|---|
| Document AI processor unavailable in preferred region | Medium × High | Verify before pinning; document a supported endpoint choice and rerun smoke tests. Gemini uses the already verified global endpoint. |
| Ground truth leaks through paths or packaging | Medium × Critical | Separate roots and loader APIs; packaging-deny test; inspect built assets and manifests. |
| Billing alert mistaken for a cap | Medium × High | Enforce durable app quotas and BigQuery limits; pause new runs at threshold. |
| Concurrent writes lose reviews/events | Medium × High | Generation preconditions and explicit conflict responses. |

## Rollback

Delete only newly created unpopulated cloud resources if the task owns them; retain smoke-test evidence and manifests. Remove the scaffold through version control, and leave billing/project state documented. No source data migration occurs in this phase.

## Todo

- [x] Scaffold and pin verified dependencies
- [x] Implement contracts and generator isolation
- [x] Implement Storage/BigQuery adapters and quotas
- [x] Complete Gemini, Document AI, BigQuery, and Storage smoke checks
- [x] Verify budget configuration and all validation gates
