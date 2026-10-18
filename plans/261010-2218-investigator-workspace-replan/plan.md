---
title: "CaseMind investigator workspace replan"
description: "Deliver all ten evidence-first investigator features with immutable sources, bounded new-data follow-up, readable exports, and release evidence."
status: in-progress
priority: P1
effort: "180-248 person-hours (low-confidence planning band)"
branch: "none (filesystem workspace)"
tags: [feature, frontend, backend, api, auth, critical]
blockedBy: []
blocks: []
created: 2026-10-10
---

# CaseMind investigator workspace replan

## Outcome and scope

Ship all ten accepted groups before the October 17 freeze: Watchlist & Screening, Source explorer, Finding cards, transaction reasons, money trail, ownership explorer, document comparison, actionable follow-up with new CSV/structured/PDF input, bounded case Q&A, actor-complete history, existing JSON, printable HTML and generated PDF. Keep one deployable service, Google Cloud AI, five scenarios, deterministic numeric/graph facts, digit-free model prose, human review, and visibly synthetic data. No graph database, enterprise workflow, real-watchlist acquisition, deployment, spending, or publication is added by this plan.

Uploaded origin and synthetic classification are separate fields. This release accepts real uploaded bytes containing supplied synthetic prototype data; it does not authorize personal/regulated real data. Existing v1 report/evidence/review bytes and hashes remain unchanged.

## Architecture and data flow

1. A minimal `ActorRef`/owner-alias contract is shared by every assessment, review, follow-up, Q&A and export. A manifest resolver returns public `CASES` to every actor and imported child manifests only to their verified owner. Every run pins a versioned snapshot identity.
2. A content-addressed catalog stores immutable structured payloads and original PDFs with hash, media type, size and object generation. Generated demo PDFs remain a compatibility adapter only.
3. Deterministic analytics emit participant/context roles, ordered transaction IDs, document lineage and coverage. Typed workspace views consume these contracts from the selected case or pinned run.
4. Authenticated follow-up streams bounded CSV/JSON/PDF input to temporary objects, quarantines unresolved records, commits an immutable child snapshot, then runs one fenced 120-second operation that publishes the cloud snapshot and optionally executes one linked child run.
5. Owner-scoped operation manifests are the recoverable authority; quota/history are idempotent projections. History is `complete_for_actor`: current anonymous-capability runs plus runs durably claimed while that proof existed. Lost-cookie legacy runs stay inaccessible.
6. Q&A retrieves one owned pinned run. Deterministic builders answer transaction/numeric questions; bounded synthesis handles other allowed families. An internal export projection renders escaped HTML and PDF while the existing report endpoint remains the sole JSON export and stays byte-compatible.

## Work packages and estimate basis

| Package | Reuse | New delta | Judgment range |
|---|---|---|---:|
| Contracts/reasons | Decimal models, analytics, pinned manifests | Versioned hashes, ActorRef/catalog/resolver, full-set query, role/order/coverage | 24–32h |
| Source workspace | Source routes, React shell, screening | Typed inventory/cards/reasons, candidate CAS, shared scope | 24–32h |
| Explorers | Raw graph, ownership/document evidence | Ordered trails, derivations, original-PDF/field lineage UI | 28–40h |
| Continuity | JSON CAS, run lease/idempotency | GIS ownership, intake/quarantine, child publish/run, history/bootstrap | 44–60h |
| Q&A/exports | Bounded model runner, report JSON, ReportLab | Scoped retrieval, shared quotas, internal HTML/PDF projection and parity | 36–48h |
| Verification/release | 13 current tests, typecheck/build | True offline evaluator/browser matrix, live gates, privacy/docs | 24–36h |

Total: 180–248 human hours. These are transparent architecture judgments, not measured velocity; the 82–124h intake research range overlaps contracts, exports and tests and is not added again. Recalibrate after Phase 1 and one Phase 2/4 work package complete using actual cycle time, including full-set retrieval, publication recovery, typed batches, actor claims and page accounting. The serial 1→4→5→6 path is 128–176h. The stated two-builder baseline at four productive hours per day for six days supplies about 48 hours, leaving a 132–200 hour aggregate gap; this is necessary-capacity arithmetic, not schedule proof. Measured team velocity and Codex wall time remain unknown.

## Phases and October 11–16 schedule

| # | Phase | Dependency | Status |
|---|---|---|---|
| 1 | [Evidence and source foundation](./phase-01-evidence-source-foundation.md) | — | Completed locally |
| 2 | [Workspace, screening and reasons](./phase-02-workspace-screening-reasons.md) | 1 | Completed locally |
| 3 | [Flow, ownership and documents](./phase-03-flow-ownership-documents.md) | 2 | Completed locally |
| 4 | [Follow-up, intake and history](./phase-04-follow-up-intake-history.md) | 1 | Completed locally |
| 5 | [Case Q&A and exports](./phase-05-qa-exports.md) | 2, 4 | Completed locally |
| 6 | [Verification and release readiness](./phase-06-verification-release.md) | 3, 5 | In progress: live gates pending |

| Date | Backend lane | UI lane | Integration-owner exit gate |
|---|---|---|---|
| Oct 11 | Freeze contracts/catalog/resolver/reasons | Freeze scoped selection contracts | Phase 1 gates; legacy bytes captured; estimate recalibrated |
| Oct 12 | Source/screening/reason services | Sources, Watchlist, cards, reasons | Phase 2 API/UI gate |
| Oct 13 | Explorer services; auth/owner index | Money, ownership, document views | Phase 3 deterministic/responsive gate |
| Oct 14 | Intake/quarantine/child publish/run/history | Follow-up/intake/history states | Phase 4 restart/history gate; estimate recalibrated |
| Oct 15 | Q&A/export renderers | Q&A and export controls | Phase 5 scope/parity/security gate |
| Oct 16 | Offline and authorized live readiness evidence | Offline browser matrix | All required gates, privacy review, docs, checklist |

The date is high risk. Aggregate capacity does not remove the serial path. One integration owner alone edits `models.py`, `main.py`, `api.ts`, `main.tsx`, `styles.css`, dependency manifests and shared test fixtures at daily checkpoints; phase lanes own only their listed new modules/components/tests. No builder count is asserted as sufficient.

## Compatibility, rollback and success

- Legacy snapshot hashes are verified from the raw stored canonical case before model adaptation. V1 snapshot IDs flow unchanged through run, cloud query/extraction and report; v2 hashes cover the explicit manifest. New optional fields never silently change a legacy digest. Existing report bytes are never rewritten, and their evidence/list order is treated as unknown rather than semantic.
- Back up persistent prefixes and checksums before schema/index changes. Rollback disables new routes/UI and restores explicit backups; never use Git checkout as data rollback. Recovery repairs projections and marks interrupted operations without retrying provider work.
- [x] All ten groups work across five scenarios with resolvable evidence, visible uncertainty and synthetic labels.
- [x] Uploaded synthetic CSV/JSON/PDF originals survive restart; history is complete for the proven actor boundary; old artifact bytes remain unchanged.
- [x] Q&A abstains outside scope; existing JSON, HTML and PDF agree on canonical facts and work offline.
- [ ] Offline gates pass; real GIS/GCS/Document AI/Gemini/tool and deployed browser gates also pass before release-ready is claimed.

Research: [brainstorm](../reports/brainstorm-261010-2204-investigator-workspace-features.md), [foundations](./reports/research-foundations.md), [intake](./reports/research-intake.md). Required before authenticated/live gates: GIS audience/allowlist/signing secret, verified pinned parsers, and authorization for cloud/config/deploy. Publication is separate.

Accepted choices are fixed for execution: all ten groups before the freeze; follow-up includes actual new synthetic CSV/structured/PDF input; exports include existing JSON, printable HTML and generated PDF. Do not re-open these as validation questions.

Review: [decisions and validation](./reports/review-validation.md). This supersedes the [previous plan](../261010-2210-investigator-workspace/plan.md). Unchecked phase criteria are the durable task tracker. Phases 1–5 are locally complete; Phase 6 retains the live and final bundle-review gates.

Execution: [implementation and verification report](../reports/cook-261011-1326-investigator-workspace.md). All ten groups are implemented, with 87 Python and 19 browser tests passing. No deployment or cloud spending occurred; this extension is not yet release-ready.

<!-- slug: investigator-workspace-replan -->
