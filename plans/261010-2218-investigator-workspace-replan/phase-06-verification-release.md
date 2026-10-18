---
phase: 6
title: "Verification and release readiness"
status: in-progress
priority: P1
effort: "24-36 person-hours"
dependencies: [3, 5]
---

# Phase 6: Verification and release readiness

## Goal

Prove all ten groups across five scenarios, verify real provider/model/tool behavior, update docs from evidence, and assemble a release-ready bundle without deploying, spending, configuring OAuth/cloud resources or publishing under this plan.

## Verified context

- Non-live evaluator still constructs `Cloud`, calls `load_case`, and calls cloud extraction (`evaluation/run-evaluation.py:70-74,98-131`). It can bill and is not an offline gate.
- Playwright runs live investigations and package exposes only `test:e2e` (`frontend/e2e/investigation.spec.ts:4-52`; `frontend/package.json:6-10`).
- The prototype brief owns navigation and project context records measured state (`docs/prototype-brief.md:1-40`; `docs/project-context.md:1-40`).
- Research verified the current 13 Python tests, typecheck and build pass; they cover only current behavior. Offline fixtures cannot establish live Gemini/Document AI/GIS/deployed quality.

## Test matrix and release states

| Layer | Offline/non-billable gate | Live gate after authorization |
|---|---|---|
| Unit | Legacy bytes, full-set order/hash, ActorRef, screening/ownership/docs, typed intake, Q&A/exports | None |
| API | Revoked sessions, streaming caps, operation crashes/fences, scoped history, publication reconciliation, page quota/parity | GIS configured client; GCS generations; uploaded PDF via Document AI |
| Evaluation | Five generated scenarios plus controls; zero Cloud construction/calls | Five-scenario Gemini/tool run with approved parameters |
| Browser | Seeded test server: ten groups, 375/768/1440, keyboard/all states | Deployed anonymous plus authenticated intake/history |
| Operations | Static config/secret/bundle/rollback review | Build/deploy/smoke/log/rollback revision separately authorized |

Offline pass means implementation complete and awaiting live validation. Release-ready requires every live row. Publication remains separate.

## Files and ownership

| Action | Absolute path | Owner/change |
|---|---|---|
| Modify | `/Users/thangluu/Repos/casemind-ai/evaluation/run-evaluation.py` | Backend verification: true offline path and explicit live Cloud construction. |
| Create | `/Users/thangluu/Repos/casemind-ai/tests/offline_workspace_server.py` | Backend verification: test-only seeded real routes/store. |
| Create | `/Users/thangluu/Repos/casemind-ai/frontend/playwright.offline.config.ts` | UI verification: deterministic fixed-port lifecycle. |
| Create | `/Users/thangluu/Repos/casemind-ai/frontend/e2e/workspace-offline.spec.ts` | UI verification: ten-group responsive/keyboard/failure matrix. |
| Modify | `/Users/thangluu/Repos/casemind-ai/frontend/package.json` | Integration owner: explicit offline/live scripts. |
| Modify | `/Users/thangluu/Repos/casemind-ai/frontend/playwright.config.ts` | Integration owner: live target explicit. |
| Modify | `/Users/thangluu/Repos/casemind-ai/docs/prototype-brief.md` | Docs owner: verified experience and links. |
| Modify | `/Users/thangluu/Repos/casemind-ai/docs/project-context.md` | Docs owner: measured status/prerequisites. |
| Modify | `/Users/thangluu/Repos/casemind-ai/docs/cloud-setup.md` | Docs owner: only live-verified routes. |
| Modify | `/Users/thangluu/Repos/casemind-ai/docs/data-model.md` | Docs owner: implemented contracts. |
| Modify | `/Users/thangluu/Repos/casemind-ai/docs/system-architecture.md` | Docs owner: one-service flows/quotas/recovery. |
| Modify | `/Users/thangluu/Repos/casemind-ai/docs/evaluation-design.md` | Docs owner: matrix/semantic rubric. |

No deploy-script change is planned unless authorized live evidence proves its route wrong.

## Implementation steps

1. Refactor evaluator so offline mode never reads cloud config/credentials or constructs/calls Storage, BigQuery, Document AI or Gemini. Fixtures stay under evaluation/tests and assert zero Cloud calls.
2. Preserve `--split`, `--live`, `--repeats`, `--concurrency`; name artifacts by mode/scenario/control/code/config/time and keep ground truth outside runtime/public bundles.
3. Create seeded server with production routes/contracts and immutable artifacts. Use deterministic port; check owner, track PID/command/port/workspace and stop only the harness process.
4. Cover all ten groups/five scenarios at three widths with keyboard, public demos while signed in, stale scope, loading/empty/error, restart, quota, quarantine, inert document pages, exports and cross-owner denial.
5. Run narrow phase gates, then full offline suite. Preserve failures and fix behavior.
6. Review evidence/privacy/security: no ground truth or secrets; facts resolve; origin/classification differ; uncertainty/no-criminality language remains; originals download only as attachment; no active PDF content, private URLs/objects or revoked sessions leak.
7. After explicit authorization, verify GIS, GCS original bytes/generation, Document AI, Gemini/tool semantics and deployed browser. Record config/revision/log/artifact/rollback evidence; unrun/failed gate leaves pending.
8. Update only owning docs and assemble source/tests/build/evaluation/privacy/checklist bundle.

## Offline commands

```bash
./.venv/bin/python -m pytest tests -m "not live_gcp" -q
./.venv/bin/python -m ruff check backend tests evaluation
npm --prefix frontend run typecheck
npm --prefix frontend run build
PYTHONPATH=backend ./.venv/bin/python evaluation/run-evaluation.py --split all --repeats 1 --concurrency 1
npm --prefix frontend run test:e2e:offline
```

Repeat with cloud config/credentials absent and assert zero Cloud client/provider calls.

## Later-authorized live gates

```bash
PYTHONPATH=backend ./.venv/bin/python evaluation/run-evaluation.py --split all --live --repeats 1 --concurrency 1
CASEMIND_TEST_URL="https://<authorized-url>" npm --prefix frontend run test:e2e:live
```

First review project/region/bucket/processor/model/GIS/secrets/image/budget. Verify 501- and 5,000-row pinned snapshots reach analytics completely; reconcile an interrupted publication; prove actual per-attempt PDF page reservation; retain one uploaded PDF hash across GCS, Document AI, inert derivative, report and export. Run semantic Q&A grading and all scenarios. Deploy/smoke/log commands need separate authorization and a recorded rollback revision.

## Risks and rollback

| Risk | Likelihood × impact | Mitigation |
|---|---|---|
| Freeze capacity insufficient | High × High | Daily gates/integration owner; report blocker without cutting scope. |
| Offline path still bills | Medium × High | Dependency injection, absent credentials and no-client assertion. |
| Fixtures enter production | Low × High | Tests-only placement, packaging/import scan. |
| Live quality fails late | High × High | Keep pending; retain evidence and fix before readiness. |
| Docs overclaim | Medium × High | Cite artifacts and list every unrun gate. |
| Security/recovery fixtures miss provider boundaries | Medium × High | Live GIS/GCS/Document AI tests plus fence/request-hash/crash injection before release-ready. |

Back up persistent state/config before live checks. Roll back feature flags/routes or recorded revision only under authorization; restore data from backups, never Git checkout.

## Done

- [x] Full offline suite/evaluator/browser pass with zero Cloud calls.
- [ ] Evidence/privacy/secret review passes for all features/scenarios.
- [ ] Real GIS/GCS/Document AI/Gemini/tool/deployed browser gates pass before release-ready.
- [x] Docs/checklist cite evidence and keep deploy/publication separately authorized.

## Execution evidence

87 Python tests, lint, typecheck/build and 19 offline browser tests pass. Fifty
generated cases yield 45 TP / 0 FP / 0 FN in the template metric. Source/packaging
privacy review and scoped access checks pass; direct compiled-bundle text inspection
was blocked by the environment filter and remains unverified. Real GIS/provider/
deployed gates remain pending. See the [execution report](../reports/cook-261011-1326-investigator-workspace.md).
