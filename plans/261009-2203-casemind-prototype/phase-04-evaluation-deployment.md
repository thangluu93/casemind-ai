# Phase 4: Evaluation, Reliability, and Deployment

## Overview

- **Status:** Delivered with unmet research gates
- **Priority:** P1
- **Effort:** 16h
- **Dependency:** Phases 1–3 complete
- **Objective:** measure the full system on frozen hidden truth, enforce release gates and usage controls, deploy one verified Cloud Run revision, and preserve rollback/log routes for the current prototype; October 17 freeze remains future work.

## Context and Invariants

- The evaluation suite requires exact deterministic results, 100% citation resolution, screening restraint, document accuracy, persistent reviews, and bounded runtime ([release gates](../../docs/evaluation-design.md#metrics-and-proposed-release-gates)).
- Mutation, provider, reconnect, restart, concurrent review, and prompt-injection tests are required ([verification methods](../../docs/evaluation-design.md#verification-methods)).
- Deployment must use one container and record the verified operational route ([implementation roadmap](../../docs/implementation-roadmap.md#suggested-implementation-boundaries)).

## Data Flow

1. The evaluator loads frozen case inputs through the same public runtime path and loads hidden truth through a separate evaluator-only identity/path.
2. It runs deterministic-only and live-agent variants, capturing raw TP/FP/FN, citation resolution, exact path/amount fields, document fields, review behavior, latency, calls, tokens, pages, BigQuery bytes, and cost.
3. Results are written to a private versioned evaluation prefix; only aggregate metrics, counts, failures, configuration hashes, and limitations enter deployment artifacts.
4. The release gate builds the React bundle into the Python container, deploys a single Cloud Run revision, runs fresh-session smoke/restart/reconnect checks, and records revision, log query, usage policy, and rollback command.

## Actual Files

- Evaluation: `evaluation/{run-evaluation,rescore-label-construction}.py`; private results under ignored `evaluation-output/`.
- Reliability: focused tests plus live `frontend/e2e/investigation.spec.ts`.
- Deployment: `Dockerfile`, `.dockerignore`, `.gcloudignore`, `scripts/deploy-cloud-run.sh`, `scripts/configure-runtime.py`.
- Operations: `docs/cloud-setup.md`; evidence report under `plans/reports/`.

## Implementation Steps

1. Freeze generator, input, truth, prompt, tool, policy, and evaluation hashes. Confirm truth is absent from images, runtime service account access, prompts, tools, retrieval, logs, frontend bundle, and public demo objects.
2. Run 20 development and 30 held-out cases, with three live-agent runs per held-out case. Report raw counts and variation; never tune using held-out labels.
3. Compare deterministic-only and agent runs. Attribute calculations to tools and synthesis quality to Gemini; use human checks for claim support rather than a model judge as ground truth.
4. Gate release on exact bounded analytics, 100% citation scope/resolution, zero unsupported identity links or accusations, all screening safety controls, required demo document fields correct or unresolved, and version-bound review persistence after restart. Report target misses instead of hiding them.
5. Measure warm/cold latency, deadline termination, provider retries, calls/tokens/pages/bytes, and first-five-run cost forecast. Confirm durable global/session quotas pause new work while reads remain available.
6. Build one container, run local system tests, deploy to Cloud Run under the scoped service account, and verify from a fresh browser session. Record chosen project/region/model/processor, revision, log query, budget/alert verification, and exact rollback route.
7. Freeze implementation and deployment on October 17. Prepare evidence needed for later deck/video/repository work, but do not publish GitHub or submit to the competition without separate authorization.

## Validation

Use the prepared Python environment. Live evaluation consumes the persistent allowance; do not rerun merely to repeat a passing check.

```bash
python -m pytest -q
CASEMIND_USE_GCLOUD=true python evaluation/run-evaluation.py --split held-out --live --repeats 3 --concurrency 3
npm --prefix frontend run build
sh scripts/deploy-cloud-run.sh
```

Measured results, actual files, remaining gates and rollback route: [delivery evidence](../reports/261009-prototype-delivery.md). Original planned fixture/module splits were consolidated into the current source files; the source tree is authoritative.

## Risks and Mitigations

| Risk | Likelihood × impact | Mitigation |
|---|---|---|
| Held-out metrics miss proposed targets | Medium × High | Fix evidence/safety defects; report remaining metric gap with counts. Never tune against hidden labels or fabricate success. |
| Deployment cost or quota grows unexpectedly | Medium × High | Minimum instances off unless justified, bounded inputs, durable quotas, BigQuery byte caps, alerts, and daily usage review. |
| Cloud Run restart loses workflow state | Medium × Critical | All step events/artifacts in Storage; snapshots in BigQuery; explicit interrupted state and new attempt. |
| Deployment revision is bad near freeze | Medium × High | Traffic rollback to the last verified revision; keep compatible immutable schema/input versions. |

## Rollback

Route traffic to the last verified Cloud Run revision, stop new runs if schemas are incompatible, and keep all immutable inputs, reports, reviews, evaluation outputs, and logs. Remove only resources created by this implementation after ownership and retention checks.

## Todo

- [ ] Complete preregistered source freeze and independent topology-family holdout; packaging/input separation verified
- [x] Run 90 live held-out-seed repetitions and focused mutation/reliability tests; document accuracy target missed
- [x] Verify quotas, cost evidence, restart, and reconnect behavior
- [x] Deploy and record logs/rollback for the current prototype; October 17 freeze remains future work
