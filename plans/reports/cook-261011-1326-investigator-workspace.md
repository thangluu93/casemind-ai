# Investigator workspace implementation report

Date: 2026-10-11, Asia/Ho_Chi_Minh. Workflow: ak-cook.
Plan: [accepted six-phase plan](../261010-2218-investigator-workspace-replan/plan.md).

## Result and phase state

All ten requested feature groups are implemented locally. Phases 1–5 are complete
against their offline acceptance gates. Phase 6 offline verification, documentation
and review are complete; its real authentication/provider/deployed gates remain
pending. The extension is not release-ready and has not been deployed.

Watchlist is now a visible workspace tab beside Overview. The other tabs expose
sources, finding cards, why a selected transaction is suspected, money trails,
ownership, document comparison, actionable new-data follow-up, case Q&A and
history. Report controls retain JSON and add printable HTML/generated PDF.
See [implemented behavior and contracts](../../docs/investigator-workspace.md).

## Delivered scope

- Immutable v1-compatible snapshots and v2 owner/parent/source manifests; exact
  original-object generations; source provenance and synthetic labels.
- Deterministic reasons with actual target/context roles, ordered transactions,
  rule parameters, limitations, legitimate alternatives and not-evaluated states.
- Source search, candidate preview and immutable human screening assessment,
  bounded exact-value explorers and separately hashed inert PDF page previews.
- Revocable GIS sessions and proven anonymous ownership claims; streamed supplied
  synthetic CSV/JSON/PDF, staged cleanup, whole-batch quarantine and immutable child
  commits. Notes alone do not call providers; execute explicitly creates a linked run.
- Canonical idempotency, quota/history projections, absolute 120-second fenced
  execution and cursor-based recovery that never retries provider work.
- Cited deterministic numeric Q&A, pinned source-inventory navigation and one
  bounded tool-free synthesis path; version-bound human review remains required.
- One allowlisted HTML/PDF projection, byte/hash-compatible existing JSON, exact
  Decimal/currency values and no full OCR document copied into new reports/exports.

No feature group was removed or deferred from local implementation. Existing
stored report/review/source artifacts were not migrated or rewritten; tests used
temporary stores. No persistent-data backup was necessary because persistent
application data was not modified.

## Final verification

| Gate | Command / evidence | Result |
|---|---|---|
| Python | `./.venv/bin/python -m pytest -q` | 87 passed; one existing Starlette/httpx deprecation warning |
| Lint | `./.venv/bin/python -m ruff check backend tests evaluation scripts` | Passed |
| TypeScript | `npm --prefix frontend run typecheck` | Passed |
| Frontend build | `npm --prefix frontend run build` | Passed |
| Browser | `npm --prefix frontend run test:e2e:offline` | 19 passed, 19.6 seconds |
| Offline evaluator | `PYTHONPATH=backend ./.venv/bin/python evaluation/run-evaluation.py --split all --repeats 1 --concurrency 1` | 50 cases; 45 TP, 0 FP, 0 FN, no errors; valid citation/source membership |
| Independent review | [final review](code-review-261011-workspace.md) | No open Critical/High/Medium offline defects |

Evaluator evidence: [summary](../../evaluation-output/run-20261011-134935/summary.json),
[retained log](../261010-2218-investigator-workspace-replan/reports/offline-evaluation-final.log).
Source hash at both evaluator start and finish:
`165567a7e66d6f3f4a57f8733c1248eaf41bced39e333c89fe2dc58e72830c11`.
The template metric does not establish real-world AML performance; OCR quality and
synthesis semantic support are not measured by offline fixtures.

Browser coverage includes five scenarios at 375/768/1440 widths, all ten loaded
tabs, keyboard source navigation, missing-run states, immutable screening/review,
Q&A replay/citations, follow-up persistence, foreign-owner denial, JSON preservation,
HTML/PDF hashes, original-PDF-to-PNG lineage and a delayed-source selection race.
Screenshots and failure artifacts are under
[plan browser artifacts](../261010-2218-investigator-workspace-replan/reports/browser-tests).

Focused regressions also prove original/50-page boundaries, 5,000 complete
transactions, forward/canonical intake dependencies, sign-out/restart revocation,
operation crashes/fence changes and recovery beyond the first hundred keys.
Document AI SDK tests prove same-original 15/15/15/5 selection, page/anchor remapping,
actual per-attempt quota, retained uncertain spend and no partial extraction cache.
Live provider behavior is still unverified.

## Review fixes and implementation adjustments

Independent review identified and verified repairs for ordinary-run fencing,
full-OCR report/export exposure, login attempt bounds, uncited exact facts,
order-dependent child identity, immutable audit collisions, recovery pagination
and stale twenty-page limits. The complete dispositions are in the review report.

The streaming transport is one raw file body per request instead of multipart.
This keeps limits effective before buffering while preserving actual supplied
CSV/JSON/PDF bytes and the accepted typed batch/counter/quarantine contracts.
Explorer components share one scoped module rather than duplicate three shells.
These implementation choices preserve the full feature scope.

The final PDF boundary check uncovered both parser/ledger caps and the provider's
synchronous limit. The parser and reservation API now accept fifty pages; the
Form Parser selects at most fifteen original pages per call. See
[official Document AI limits](https://docs.cloud.google.com/document-ai/limits).
This uses unchanged original bytes, records original pages and charges every attempt.

An older concurrent quota test assumed request zero necessarily won the thread
race. Its assertion now replays each actually successful reservation and checks
that the ledger does not change; the three-success global cap remains enforced.
The excessive-page fixture moved from twenty-one to fifty-one to match the
accepted fifty-page boundary, with real fifty-page acceptance tested separately.

Conditional Git-diff simplification was unavailable: this workspace has no Git
metadata. Review used explicit owned files. No commit or PR was created.
Earlier failures were repaired; no failing check was disabled or hidden.

## Evidence/privacy and process review

Scope checks, source resolution, unsafe PDF originals, HTML escaping, report
minimization and revoked/cross-owner access have focused tests. Runtime routes
contain no evaluation labels or ground-truth retrieval. Docker packaging excludes
tests, plans, evaluation, evaluator output, artifacts and dotfiles; only backend
code and built frontend enter the final stage. The optional direct compiled-bundle
text scan was blocked by the environment's `dist` context filter; this report
claims source/packaging review, not a completed compiled-bundle secret scan.

Playwright owned PID 12432, command `python tests/offline_workspace_server.py`,
port 8081, workspace `/Users/thangluu/Repos/casemind-ai`; it exited after the suite.
Final process checks found no listener on 8081/5173 and no remaining harness PID.
No background process was left running by this task.

## Remaining release gates

1. Supply the configured GIS web audience/origin, allowed investigator Google
   subject IDs and runtime signing-secret route. The UI currently discloses auth
   disabled when these are absent. A configuration-location question remains pending;
   no secret values are needed in chat.
2. Separately authorize live GCS generation/publication reconciliation, original-PDF
   Document AI selected-page processing and Gemini/tool/semantic-Q&A evaluation.
3. Separately authorize build/deploy, then verify anonymous and authenticated
   browser intake/history, logs, cost controls and a recorded rollback revision.

No cloud spending, OAuth/cloud configuration, deployment or publication was
performed. Earlier deployed prototype success does not verify this extension.
The October 17 full-scope decision remains unchanged. Session elapsed time is not
human team velocity; the plan's person-hour estimate is not reinterpreted as a
measured delivery capacity.

Journal: [local session record](../journals/2026-10-11-complete-investigator-workspace-implementation.md).
AgentWiki publish skipped. The report and journal are historical records; current
behavior lives in the owning product documentation.
