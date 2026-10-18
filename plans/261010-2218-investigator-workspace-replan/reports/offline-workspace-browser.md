# Offline workspace browser harness

Status: DONE_WITH_CONCERNS

## Harness

- `tests/offline_workspace_server.py` mounts the real application and its real FileStore in a temporary directory. The test-only seed endpoint writes valid pinned input manifests, evidence, report hashes and session-owned runs derived from deterministic analytics and document-field fixtures. It reads no ground truth and never substitutes a runtime model/provider response.
- `frontend/playwright.offline.config.ts` uses deterministic port 8081, one worker, retained failure traces and a Playwright-owned server process. It explicitly disables cloud and Google sign-in environment configuration. It refuses to reuse an unrelated server.
- `frontend/e2e/workspace-offline.spec.ts` contains 18 tests: fifteen case/viewport combinations, real-route checks, case-only empty states, and persisted screening/Q&A/follow-up UI actions. Each matrix test awaits actual loaded projections before asserting responsive bounds.

## Verification evidence

- Frontend build passed.
- Backend workspace/explorer/export/analytics regression including v2 snapshot identity: **18 passed**. Scoped Ruff: **passed**.
- The first browser run passed 17 tests, but its layout checks were too early during projection loading. The harness was strengthened to wait for loaded content; those early passes are not accepted as the final layout gate.
- Strengthened matrix reproduced a real mobile overflow in the loaded Ownership tab, Harbor transfer chain at 375px. Failure retained in `frontend/test-results/workspace-offline-Harbor-t-03035-n-all-ten-features-at-375px/trace.zip`. Controller notified; shared UI/CSS fixes are outside this lane's ownership.
- Independent strengthened real-route and persisted-UI actions checks: **2 passed**. They verify original-PDF attachment/CSP, exact original SHA-256 → inert PNG lineage/hash/signature, JSON byte preservation, HTML/PDF hashes, exact deterministic Q&A/replay/conflict/abstention, foreign-source/run denial, immutable review, actor-scoped history, candidate assessment persistence, follow-up creation and disabled anonymous intake/execution.
- All started servers were Playwright-owned and terminated. A final `lsof` found no listener on 8081.

## Remaining gate

Controller must fix loaded ownership mobile overflow and rerun all 18 browser tests against the rebuilt frontend. Generic ownership path IDs also require source-aware inspector mapping; fabricated display-path IDs are not resolvable source IDs.

No cloud execution, spending, deployment or publication occurred.

## Controller handoff update

The controller applied shared mobile overflow fixes and owns the final browser rerun. One lane rerun was started before the controller's stop message arrived; it passed the first two loaded mobile matrix checks, then was immediately interrupted and its owned server stopped. These partial results are not a completed release gate.

Playwright outputDir is now `plans/261010-2218-investigator-workspace-replan/reports/browser-tests`, so generated error Markdown, screenshots and retained traces live under the required plan report surface. Do not run overlapping suites sharing that output directory.

## Final controller verification

The rebuilt frontend passed all 19 tests (19.6 seconds): the original 18 plus a
delayed-source selection race. Loaded mobile overflow and source-ID mapping are
resolved. The real UI now also opens exact-Q&A source citations. Final harness
PID 12432 exited; ports 8081/5173 are clear. Current screenshots are under
`reports/browser-tests`; surviving earlier workspace failure artifacts were moved
under `reports/prior-browser-failures`. The earlier partial/failed runs are not the
final gate. See [execution report](../../reports/cook-261011-1326-investigator-workspace.md).
