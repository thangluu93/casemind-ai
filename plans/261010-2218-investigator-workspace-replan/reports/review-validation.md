# Replan review and validation

Date: 2026-10-10. Scope: planning only; application implementation remains pending.

## Accepted outcome

Retain all ten feature groups before October 17, including deterministic explanations of suspicious transaction indicators. Follow-up collects new supplied synthetic CSV/structured/PDF data. Keep the existing JSON export and add printable HTML and generated PDF. No cloud configuration, spending, deployment or publication is authorized by this planning request.

Two research reports informed six executable phases. Four independent review lenses inspected the draft against source. Findings below consolidate overlapping concerns; the original reports retain their evidence and wording.

| Concern | Disposition and plan correction |
|---|---|
| Session replay after sign-out | Accepted: opaque Store-backed revocable sessions, rotation and per-request authority checks. |
| Upload buffering/resource exhaustion | Accepted: streaming aggregate limits before buffering, conditional staging/promotion, cleanup and TTL. |
| Active original PDFs | Accepted: preserve exact attachment-only originals; separately hashed resource-bounded inert derivatives. |
| GIS versus origin/CSRF policy | Accepted: callback plus same-origin credential POST; exact CSP origins and retained write guard. |
| Publication plus analysis outlives lease | Accepted: absolute 120-second budget, remaining-time calls and fenced writes. |
| Same key with different request | Accepted: canonical request hash; conflict before quota consumption. |
| Independent CAS writes crash midway | Accepted: request-first operation authority, discoverable owner prefix and idempotent quota/history projections; recovery never retries providers. |
| History completeness exceeds available proof | Accepted: complete_for_actor, bounded durable claims, explicit lost-cookie limit and immutable old artifacts. |
| Intake ceiling exceeds query ceiling | Accepted: entire deterministic pinned set through 5,000 total rows, including inherited parent rows. |
| Partial cloud publication | Accepted: SnapshotRef intent, deterministic job identity and verified explicit reconciliation; read-only restart recovery. |
| Mixed-record dependency/order ambiguity | Accepted: versioned typed batch, explicit revisions, whole accepted-set validation and retained quarantine. |
| Actor contract arrives after assessments | Accepted: minimal ActorRef and alias contract in Phase 1. |
| Multi-page quota undercounts | Accepted with correction: verified pages reserved for each actual provider attempt; retries consume again because earlier attempts may bill, duplicate replay does not. See existing `UsageLedger.reserve_page` in `backend/casemind/store.py`. |
| Shared callers and duplicate export product | Accepted: migrate evaluator and cloud-setup callers in Phase 1; retain `/report` as sole JSON. HTML/PDF share an internal projection and trace extra sections to pinned artifacts. |
| Remove authenticated intake | Rejected: `docs/system-architecture.md:120-122` explicitly restricts public judges to preloaded synthetic cases and requires authentication for later uploads. The existing cookie proves possession of an anonymous session, not an allowlisted investigator identity (`main.py:39-57`). Keep bounded restricted auth; no enterprise identity platform is proposed. Delegated task wording alone is not user authorization. |

Whole-plan sweep also removes the hidden Phase 3→4 parser/rendering dependency: source preflight and safe derivative foundation belong to Phase 1, consumed by both explorer and intake lanes. Shared files and dependencies have explicit integration ownership.

## Validation boundaries

- CLI validation checks plan structure and six pending phases; it does not establish feature implementation or deadline feasibility.
- Final `ak plan validate ... --json` returned `valid: true`. The whole-plan sweep verified seven frontmatters, pending status, six phases, local links, existing Modify targets, no scaffold markers and the 800-line limit. Each phase has 81–105 lines; no dependency cycle remains.
- The foundations research ran the current 13 Python tests and frontend typecheck/build successfully. These establish only the existing baseline, not new feature acceptance.
- Each phase specifies focused checks, failure states, rollback and completion criteria. Proposed tests/modules/scripts remain pending until execution.
- The current evaluator's non-live path still calls cloud services. Its offline command becomes non-billable only after the planned refactor and zero-provider assertions.
- Live GIS, GCS, Document AI, Gemini/tool and deployed browser validation remain unrun. Parser/auth dependency versions must be verified and pinned during implementation.
- Estimate: 180–248 person-hours, low-confidence judgment; the documented 48-hour baseline capacity leaves 132–200 hours uncovered. The serial critical path and unknown measured velocity prevent a deadline guarantee.
- Plan files and unchecked phase criteria are the durable task tracker. No external task board was modified. Git activation is unavailable because this workspace has no Git checkout.
- Automatic journal creation previously failed because `casemind-ai` is not registered and `ak projects list --json` returned no projects. No registration/configuration was changed to work around that limitation.

## Review evidence

- [Foundations research](./research-foundations.md)
- [Intake research](./research-intake.md)
- [Security review](./red-team-security.md)
- [Failure review](./red-team-failure.md)
- [Assumptions review](./red-team-assumptions.md)
- [Scope and complexity review](./red-team-complexity.md)

Execution starts with Phase 1. Recalibrate estimates at the Phase 1 and Phase 2/4 checkpoints; preserve all accepted scope when reporting blockers.
