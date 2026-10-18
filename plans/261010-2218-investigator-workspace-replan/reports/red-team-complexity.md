# Red-team scope, complexity and contract review

## Scope
Plan-only fourth-lens review of the index, six phases and research against the
current backend/evaluator/frontend callers. No implementation was changed and no
tests, lint, typecheck or build were run.

## Findings
### High — Phase 1 changes a shared snapshot contract without owning every caller

**Plan location:** Phase 1, **Verified context**, item 3, **Contracts and data
flow**, items 3 and 5, and **Files and ownership**
(`phase-01-evidence-source-foundation.md:20,29,31,35-51`).

**Concrete failure:** Phase 1 correctly says every snapshot-identity caller must
move to versioned identity and resolved document bytes, but its file list omits
`evaluation/run-evaluation.py`. That evaluator directly computes `digest(case)`,
calls `Cloud.load_case(case)`, passes the old `investigate(case, ...)` contract,
and calls `Cloud.extract(case, doc)` and `Cloud.query_transactions(case)`
(`evaluation/run-evaluation.py:91,103,111,123-125`). The implementations being
changed currently derive identity and PDF bytes from `Case` alone
(`backend/casemind/cloud.py:54-57,80-95,99-105,128-141`) and the report independently
recomputes `digest(case)` (`backend/casemind/investigation.py:323-347`). If Phase 1
changes these signatures while deferring the evaluator to Phase 6, Phase 1 cannot
meet its own “all v1 snapshot callers remain compatible” gate; the evaluator will
either fail immediately or keep a parallel v1 identity/original-PDF path for five
more phases.

**Required correction:** Add `evaluation/run-evaluation.py` to Phase 1 ownership
and update its runtime manifest, live investigation, transaction and extraction
calls in the same contract change. Make one `SnapshotRef`/resolved-source input
the required boundary for `Cloud` and `investigate`; retain Phase 6 ownership only
for separating offline from live execution. Add a caller-completeness check to the
Phase 1 gate rather than relying on Phase 6 to repair the contract later.

### Medium — The export plan creates a second JSON product beyond the accepted formats

**Plan location:** Phase 5, **Goal**, **Q&A and export contracts**, item 5, and
**Files and ownership** (`phase-05-qa-exports.md:14,29,39-48,89`).

**Concrete failure:** The accepted feature is the existing JSON export plus new
printable HTML and generated PDF, yet Phase 5 adds
`/exports/canonical.json|html|pdf` while preserving `/report`, and tells the UI to
offer “legacy JSON plus three canonical formats.” The existing JSON contract is
already the stored immutable report returned by `/api/runs/{run_id}/report`
(`backend/casemind/main.py:303-309`), and the current UI already downloads that
route as JSON (`frontend/src/investigation-report.tsx:34-43`). A second JSON
representation adds an extra public schema, route, filename/control, parity
surface and long-term ambiguity over which JSON is authoritative. It is not
needed to render HTML/PDF and directly contradicts the plan index’s “existing
JSON plus printable HTML and generated PDF” scope (`plan.md:18`).

**Required correction:** Keep `/report` as the sole JSON export. Use `ExportView`
only as an internal projection for escaped HTML and generated PDF, with parity
checks back to the pinned report/evidence/review. Remove `canonical.json` and the
extra JSON UI control; expose only existing JSON, HTML and PDF.

### Medium — Google account identity is an unaccepted infrastructure program

**Plan location:** Phase 4, **Auth, ownership and persistence contracts**, items
1-2, **Files and ownership**, and **Implementation steps**, items 1-2
(`phase-04-follow-up-intake-history.md:26-27,39-53,57-58`).

**Concrete failure:** The accepted history design is session-owned and the new
input is explicitly synthetic, but Phase 4 adds GIS token verification, audience
and subject allowlists, signed authenticated sessions, sign-out, anonymous-run
claim tokens, CSP changes and new auth dependencies. The current service already
issues a high-entropy HttpOnly/SameSite session cookie
(`backend/casemind/main.py:39-57`), binds every run read to that session
(`backend/casemind/main.py:77-94`), and reserves/creates investigations under the
same owner (`backend/casemind/main.py:192-240`). Nothing in the ten accepted
feature groups requires cross-device identity or Google accounts. This new
identity system introduces external configuration prerequisites that the plan
itself says are unavailable, so it can block synthetic CSV/JSON/PDF intake and
history even when all requested feature code is complete.

**Required correction:** Keep prototype intake, follow-up and history scoped to
the existing anonymous session owner, adding the required upload bounds,
idempotency, quotas and immutable owner index. Remove GIS, account allowlists,
claim transfer and sign-out from this deadline plan. A durable account migration
can be a separately accepted product/security project if cross-device ownership
is later required.

## Verified non-findings
- The case resolver, content-addressed catalog, versioned manifest and exact
  original-PDF path are required by uploaded synthetic input and pinned evidence;
  they are not optional infrastructure.
- The plan explicitly serializes edits to `models.py`, `main.py`, `api.ts`,
  `main.tsx`, `styles.css`, dependency manifests and shared fixtures under one
  integration owner, so no additional shared-file collision is evidenced.
- The 180–248 hour range is labeled low-confidence judgment and the plan states
  the capacity gap; it is not presented as measured velocity.

## Unresolved questions
None. All three corrections preserve the fixed ten-feature, new synthetic
CSV/JSON/PDF intake, and existing JSON plus HTML/PDF scope.

Status: DONE_WITH_CONCERNS
Summary: The plan has one blocking caller-ownership gap and two avoidable scope expansions: a second JSON export contract and a Google identity subsystem beyond the session-owned prototype requirement.
Concerns/Blockers: Fix the Phase 1 evaluator ownership before implementation; removing the duplicate JSON route and GIS identity program materially reduces deadline risk without cutting accepted features.
