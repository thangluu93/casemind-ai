---
title: "CaseMind AI Prototype Implementation"
description: "Build and deploy the evidence-backed five-scenario CaseMind investigation prototype on Google Cloud."
status: in_progress
priority: P1
effort: 64h
branch: "none"
tags: [feature, backend, frontend, api, infra, critical]
blockedBy: []
blocks: []
created: 2026-10-09
---

# CaseMind AI Prototype Implementation

## Overview

Implement one Cloud Run service containing a FastAPI/Google ADK backend and built Vite React/TypeScript workspace. The runtime uses live Gemini, Document AI, bounded BigQuery analytics, and versioned Cloud Storage artifacts to execute all five synthetic investigation scenarios. Deterministic tools compute facts; every report claim resolves to scoped evidence; only a human can submit a version-bound review.

The accepted scope is the delivery contract in [the prototype brief](../../docs/prototype-brief.md#delivery-contract), the single-service boundary and five runtime roles in [the system architecture](../../docs/system-architecture.md#system-boundary), the records in [the data model](../../docs/data-model.md#core-records), and the five scenarios and gates in [the evaluation design](../../docs/evaluation-design.md#five-required-scenarios).

## Dependencies and Critical Path

```text
Phase 1 contracts + cloud smoke tests
  -> Phase 2 deterministic tools + live ADK investigation
    -> Phase 3 workspace + immutable human review
      -> Phase 4 held-out evaluation + Cloud Run deployment
```

- Google Cloud project number `251896792352` has billing enabled in VND. Two monthly project-filtered budgets already exist and exclude all credits (gross service spend): target `750,000 VND` with 50/80/100% thresholds and reserve ceiling `950,000 VND` with 80/100% thresholds. Application quotas remain mandatory because alerts do not stop spend.
- A live Vertex global `gemini-3.1-flash-lite` call succeeded with a 5-token response, and Google ADK `2.11.0` is installed in `.venv`. Live Document AI, BigQuery, Storage and scoped runtime IAM are verified; routes are recorded in [cloud setup](../../docs/cloud-setup.md).
- October 17 is the code/content freeze; October 18 is submission day. Deployment is in scope. Public GitHub publication and competition submission are separate actions and remain outside this plan's authorized writes.

## Phases

| Phase | Name | Status | Depends on | Effort |
|---|---|---|---|---|
| 1 | [Foundation, Contracts, and Cloud Feasibility](./phase-01-foundation-contracts-cloud.md) | Implemented | None | 14h |
| 2 | [Deterministic Investigation and ADK Runtime](./phase-02-investigation-runtime.md) | Implemented; verification limits recorded | Phase 1 | 20h |
| 3 | [Investigation Workspace and Human Review](./phase-03-workspace-human-review.md) | Implemented | Phase 2 API | 14h |
| 4 | [Evaluation, Reliability, and Deployment](./phase-04-evaluation-deployment.md) | Delivered with unmet research gates | Phases 1–3 | 16h |

## Whole-Plan Acceptance

- All five scenarios run from labeled synthetic inputs through actual deterministic tools and live Gemini synthesis; changing an input changes the affected findings without canned fallback output.
- The four specialists plus orchestrator remain distinct roles inside one bounded runtime, with at most 20 tool calls, two transient retries, and a 120-second run deadline.
- Every factual claim resolves to same-case/same-run evidence; ground truth is evaluator-only and absent from runtime bundles, prompts, tools, retrieval, logs, and deployed assets.
- BigQuery persists immutable normalized snapshots; Cloud Storage persists documents, events, evidence, reports, reviews, and shared usage state using generation preconditions.
- The workspace renders timeline, directed graph, evidence/source inspection, structured report, uncertainty/synthetic labels, and approve/reject/follow-up reviews bound to an immutable report version.
- Focused tests, live-provider integration tests, all-scenario evaluation, restart/reconnect checks, and Cloud Run smoke tests pass. Measured failures and costs remain visible.

## Rollback

Each phase is additive and versioned. Revert application code to the last passing revision, retain immutable source/run/report/review objects, and redeploy the last verified Cloud Run revision. Never mutate evidence or evaluation labels to make a revision pass.

## Unresolved External Checks

- Independent topology-family holdout, human semantic-support review, complete prompt-injection/deadline fault testing and the document-recall target remain unmet. See [delivery evidence](../reports/261009-prototype-delivery.md).
- IBM archive access/licensing and OpenSanctions competition use may remain pending without blocking the five independent CaseMind synthetic scenarios.
