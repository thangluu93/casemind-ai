---
title: "CaseMind investigator workspace"
description: "Deliver all ten evidence-first investigator workspace feature groups through six dependency-ordered phases."
status: pending
priority: P1
effort: "180-248 person-hours"
branch: "none (workspace is not a Git checkout)"
tags: [feature, frontend, backend, api, critical]
blockedBy: []
blocks: []
created: 2026-10-10
---

# CaseMind investigator workspace

Superseded by the [reviewed investigator workspace replan](../261010-2218-investigator-workspace-replan/plan.md). This record remains historical; use the new plan for execution and current estimates.

## Overview

Evolve the existing single-service prototype into an evidence-first investigator
workspace covering Watchlist & Screening, Sources, Finding cards, transaction
reasons, Money trail, Ownership, Documents, Follow-up, Case Q&A, and History and
exports. Deterministic facts remain separate from model interpretation and every
fact stays scoped to resolvable evidence and a human decision.

## Confirmed delivery decisions

- Deliver all ten feature groups before the October 17 freeze. This is the target,
  not a guarantee; the capacity gap and prerequisites are explicit below.
- Candidate assessments are independent immutable records. Follow-up supports
  existing checks, notes, outstanding requests, and restricted CSV/PDF/structured
  new-data intake that produces a new immutable snapshot and analysis run.
- Offline exports include printable HTML, generated PDF and existing JSON.
- No cloud spend, deployment, publication, external watchlist, or public sharing
  is authorized by this plan. A later release action requires explicit authority.

## Dependency graph

`01 contracts` → (`02 evidence UI` → `03 explorers`) and (`04 continuity/intake`);
`02 + 04` → `05 Q&A/exports`; `03 + 05` → `06 evaluation/release readiness`.

Parallel execution is allowed only for disjoint files. One integration owner must
serialize shared-file changes. Durable phase checkboxes are the task tracker; no
external task system is used.

## Phases

| # | Phase | Status | Effort | Depends on |
|---|---|---|---:|---|
| 1 | [Evidence and transaction-reason contracts](./phase-01-contract-foundation.md) | Pending | 24-32h | — |
| 2 | [Sources, watchlist, finding cards and reasons UI](./phase-02-sources-watchlist-findings-ui.md) | Pending | 24-32h | 1 |
| 3 | [Money, ownership and document explorers](./phase-03-investigation-explorers.md) | Pending | 28-40h | 2 |
| 4 | [Bounded follow-up, restricted intake and durable history](./phase-04-follow-up-history.md) | Pending | 44-60h | 1 |
| 5 | [Scoped case Q&A and offline exports](./phase-05-case-qa-exports.md) | Pending | 36-48h | 2, 4 |
| 6 | [Evaluation, documentation and release readiness](./phase-06-evaluation-release-readiness.md) | Pending | 24-36h | 3, 5 |

## Success criteria

- [ ] All ten feature groups work across the five required synthetic scenarios.
- [ ] Four domain specialists plus orchestrator remain in one deployable service;
      human review remains required for every disposition.
- [ ] Every displayed fact resolves to a current-case or pinned-run source; no
      ground truth, cross-session data, unsupported ordering, or crime inference leaks.
- [ ] Reviews and candidate assessments are immutable; follow-up and Q&A are
      idempotent, quota-reserved, deadline-bounded, and recover after restart.
- [ ] Existing report JSON remains readable; HTML/PDF exports preserve exact
      decimals, labels, limitations, hashes, review versions, and safe escaping.
- [ ] Offline deterministic and UI gates pass before any explicitly authorized,
      billed model/browser evaluation or deployment step.
- [ ] Full release readiness remains pending until authorized live model/tool,
      restricted-auth and deployed browser gates also pass.

## Release feasibility

The documented October 11-16 window offers at most about 48 person-hours at two
builders times four hours per day, with availability still unverified. The 180-248
hour plan has a 132-200 hour gap. Meeting the confirmed target mathematically needs
roughly six to nine additional similarly capable builders plus an integration owner;
onboarding and shared-file gates keep the schedule high risk. Phase 6 contains the
daily target and external OAuth/auth configuration prerequisites.

<!-- slug: investigator-workspace -->
