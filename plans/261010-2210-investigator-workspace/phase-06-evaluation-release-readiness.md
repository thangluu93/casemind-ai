---
phase: 6
title: "Evaluation, documentation and release readiness"
status: pending
priority: P1
effort: "24-36 person-hours"
dependencies: [3, 5]
---

# Phase 6: Evaluation, documentation and release readiness

## Goal

Prove all ten groups across five synthetic scenarios, update the smallest owning
docs, and prepare a reviewable release bundle without spending cloud budget,
deploying, publishing, or changing external OAuth/cloud resources.

## Context and verified foundations

- The evaluator currently reads `artifacts/cloud-config.json`, constructs `Cloud`,
  loads/query cases and extracts documents even without `--live`
  (`evaluation/run-evaluation.py:70`). Its default is not an offline gate.
- The existing Playwright test starts five live investigations and waits for
  provider-backed reports (`frontend/e2e/investigation.spec.ts:4`). It is billed/live.
- Current deployment is one unauthenticated Cloud Run service
  (`scripts/deploy-cloud-run.sh:11`), and no OAuth client/allowlist/signing-secret
  configuration is established by this plan.
- Current measured state belongs in `docs/project-context.md:5`; proposed targets
  must not be reported there as verified until the gates actually pass.

## Requirements

- [ ] Create a truly offline deterministic evaluator path that never reads cloud
      config, credentials, Storage, BigQuery, Document AI or Gemini unless `--live`
      is explicit. Keep evaluator truth outside runtime inputs and bundles.
- [ ] Create a test-only seeded workspace server and Playwright config for offline
      UI flows; no fake report/demo behavior enters production code.
- [ ] Cover layering, ownership discrepancy, screening disambiguation, KYC/document
      inconsistency and circular transfer, including positive and negative controls.
- [ ] Validate desktop/mobile, keyboard, loading, empty, success, failure,
      interruption/restart, quota, idempotency, quarantine and cross-owner denial.
- [ ] Treat live model evaluation, existing browser e2e, OAuth setup, deployment,
      smoke test, public repository and submission as explicit later-authorized
      actions. Label every command that may bill or mutate cloud state.
- [ ] Update data model, architecture, evaluation and user-facing prototype docs
      only with implemented/verified behavior. Record exact auth/intake/deploy/log/
      rollback routes only after their live verification.
- [ ] Release bundle contains source/tests/build outputs, offline evaluation report,
      evidence/privacy review and a deployment checklist; it contains no secrets,
      credentials, personal data, ground truth or unapproved archives.

## Test matrix

| Layer | Offline gate | Live/billed gate after authorization |
|---|---|---|
| Unit | Attribution, order, Decimal, screening identity, ownership, documents, escaping | None |
| API/integration | Scope, auth boundaries, intake quarantine, CAS/history, Q&A validation, export parity | Token verification against configured OAuth client if required |
| Evaluation | All five generated scenarios and controls with evaluator-only provider fixtures | `evaluation/run-evaluation.py --live` with approved split/repeats/concurrency |
| Browser | Test-only seeded reports for ten-group flows at 375/768/1440 and keyboard | Existing live investigation/review flow against authorized deployment |
| Operations | Static config/script review, secret scan, rollback checklist | Build/deploy/smoke/log checks only after explicit authorization |

## Files to modify or create

| Action | Absolute path | Change |
|---|---|---|
| Modify | `/Users/thangluu/Repos/casemind-ai/evaluation/run-evaluation.py` | Separate offline analytics startup from explicit `--live` cloud construction. |
| Create | `/Users/thangluu/Repos/casemind-ai/tests/offline_workspace_server.py` | Test-only seeded store/server for browser validation. |
| Create | `/Users/thangluu/Repos/casemind-ai/frontend/playwright.offline.config.ts` | Deterministic server lifecycle and fixed port. |
| Create | `/Users/thangluu/Repos/casemind-ai/frontend/e2e/workspace-offline.spec.ts` | Ten-group responsive/keyboard/error flow. |
| Modify | `/Users/thangluu/Repos/casemind-ai/frontend/package.json` | Separate offline and explicitly named live e2e commands. |
| Modify | `/Users/thangluu/Repos/casemind-ai/frontend/playwright.config.ts` | Keep live target explicit and prevent accidental local ambiguity. |
| Modify | `/Users/thangluu/Repos/casemind-ai/scripts/deploy-cloud-run.sh` | Prepare fail-closed auth/intake configuration consumption; do not execute it. |
| Modify | `/Users/thangluu/Repos/casemind-ai/docs/data-model.md` | Implemented attribution, assessment, intake, history, Q&A/export contracts. |
| Modify | `/Users/thangluu/Repos/casemind-ai/docs/system-architecture.md` | One-service flows, trust boundaries, quotas, auth and rollback. |
| Modify | `/Users/thangluu/Repos/casemind-ai/docs/evaluation-design.md` | Offline/live separation and full test matrix. |
| Modify | `/Users/thangluu/Repos/casemind-ai/docs/prototype-brief.md` | User-visible ten-group experience after verification. |
| Modify | `/Users/thangluu/Repos/casemind-ai/docs/project-context.md` | Only newly measured facts and remaining release prerequisites. |

No deployment output or external configuration is created in this phase. The
offline server is test-only and must be excluded from production packaging.

## Implementation steps

1. Refactor evaluator startup so the default path uses local generated `Case`
   objects and evaluator-only extraction fixtures. Construct `Cloud`, read cloud
   config and reserve provider usage only inside explicit `--live` control flow.
   Preserve existing `--split`, `--live`, `--repeats` and `--concurrency` flags.
2. Build the test-only seeded server and offline Playwright config with a fixed
   port. Check for an existing owner first, track PID/command/port/workspace, and
   terminate only the process started by the test harness.
3. Add browser flows for all ten groups, exact scope labels, reasons, explorers,
   assessments, intake/quarantine, history, Q&A fixtures and export downloads.
4. Run the narrow gates below, then the offline full suite/evaluator/browser build.
   Preserve failure output and fix behavior rather than weaken assertions.
5. Perform evidence/privacy review: no ground truth in runtime/bundles; all factual
   claims resolvable; synthetic/provenance labels present; no cross-owner access;
   no criminality inference or hidden source-access dependency in exports.
6. Update owning docs from observed results and prepare a release checklist that
   names still-unperformed OAuth/cloud/deploy/live-evaluation/publication actions.

## Offline verification gates

```bash
./.venv/bin/python -m pytest tests -m "not live_gcp" -q
./.venv/bin/python -m ruff check backend tests evaluation
npm --prefix frontend run typecheck
npm --prefix frontend run build
PYTHONPATH=backend ./.venv/bin/python evaluation/run-evaluation.py --split all --repeats 1 --concurrency 1
npm --prefix frontend run test:e2e:offline
```

After implementation, verify the offline evaluator with network credentials
absent and assert it creates no cloud client. The existing live commands are not
part of this planning authorization.

## Later-authorized live acceptance gates

These remain required for full release readiness but must not run until the user
authorizes billed/mutating cloud work and OAuth prerequisites exist:

```bash
PYTHONPATH=backend ./.venv/bin/python evaluation/run-evaluation.py --split all --live --repeats 1 --concurrency 1
CASEMIND_TEST_URL="https://<authorized-cloud-run-url>" npm --prefix frontend run test:e2e:live
```

Run the repository's deploy and smoke scripts only under that same authorization,
after reviewing their resolved project, region, image, secret and OAuth settings.
Capture the deployment revision, logs, live evaluation artifact, browser output and
rollback revision. Any missing/failed live gate leaves phase 6 pending.

## Requested October 11-16 target and capacity

The full six-phase estimate is 180-248 human builder-hours. Two builders at four
hours per day provide at most 48 hours from October 11 through 16, assuming full
availability. The minimum gap is 132 hours; the high estimate gap is 200 hours.
Mathematically, meeting the date requires about 30-41 person-hours per day, equal
to roughly eight to eleven builders at four productive hours per day (six to nine
additional similarly capable builders), plus an integration owner. Onboarding and
shared-file sequencing mean resources will not scale linearly, so this remains a
high-risk target rather than a promise.

Target integration sequence if those prerequisites are met:

| Date | Required exit state |
|---|---|
| Oct 11 | Phase 1 contracts, compatibility and deterministic reason gates green |
| Oct 12 | Phase 2 source/screening/cards/reasons integrated; phase 4 auth/history foundations underway |
| Oct 13 | Phase 3 explorers integrated; OAuth client, allowlist and secret available for restricted intake |
| Oct 14 | Phase 4 intake/follow-up/history complete; phase 5 bounded Q&A/export integration underway |
| Oct 15 | Phase 5 complete; all feature integration, regression and evidence/privacy fixes |
| Oct 16 | Phase 6 full offline evaluation/browser/docs/release bundle and freeze review |

Phase 4 may start after phase 1 while phase 2/3 UI work proceeds, and phase 5 may
start after phase 2 contracts plus phase 4 reservations/intake bindings. Parallel
work must use disjoint files; one integration owner serializes edits to shared
`models.py`, `main.py`, `api.ts`, `main.tsx` and `styles.css` at daily checkpoints.

## Success criteria

- [ ] Offline commands run with no cloud client/credentials and pass all five scenarios.
- [ ] Test-only browser flow covers every feature group and required UI state.
- [ ] Live/billed and mutating commands are separately named and never run implicitly.
- [ ] After explicit authorization, the live five-scenario model/tool evaluation,
      restricted-auth integration and deployed browser flow pass. Until then,
      release readiness remains pending even when every offline gate is green.
- [ ] Docs distinguish verified results, proposals and unperformed external setup.
- [ ] Release bundle passes evidence/privacy/secret review and is reviewable before
      any separately authorized deployment or publication.

## Risks and rollback

| Risk | Likelihood × impact | Mitigation |
|---|---|---|
| Deadline capacity is insufficient | High × High | Secure named added capacity immediately, daily integration gates, preserve full scope and report blockers without hiding cuts. |
| Offline evaluator still touches cloud | Medium × High | Dependency injection, credential-free CI and explicit no-client assertion. |
| Test fixtures leak into runtime | Low × High | Keep under tests, packaging exclusion and production import scan. |
| Release docs overclaim readiness | Medium × High | Cite measured artifacts and leave unperformed actions explicit. |

Before changing release scripts or owning docs in this non-Git workspace, copy the
exact files to a dated local backup outside deploy inputs and record checksums.
Rollback restores those explicit backups; never deploy rollback automatically.
Retain failing evaluation artifacts for diagnosis, excluding private truth from
any public or demo bundle.

## Todo

- [ ] Separate offline and live evaluation/browser paths.
- [ ] Execute the offline full matrix and evidence/privacy review.
- [ ] Update owning docs and assemble a no-deploy release bundle.
