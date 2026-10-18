# CaseMind prototype delivery evidence

## Outcome and operational route

The requested brainstorm, implementation plan, live-provider prototype and cloud deployment are delivered. The latest user constraint is gross prototype/demo GCP usage under 1,000,000 VND, regardless of credits. The forecast is below this amount; this is not a provider-enforced spending cap. Proposed research release gates remain partially unmet.

- Workspace: https://casemind-ai-q36bubsb3a-as.a.run.app
- Project: `casemind-ai`, number `251896792352`; Cloud Run `asia-southeast1`.
- Current revision: `casemind-ai-00006-dtd`, 100% traffic; health `/api/health`.
- Runtime: FastAPI, Google ADK 2.11.0, four specialists and one orchestrator; actual global Vertex `gemini-3.1-flash-lite`, Document AI, BigQuery and GCS.
- Five independent labeled synthetic demo cases: layering, ownership/declaration discrepancy, watchlist disambiguation, KYC inconsistency and temporal circular transfers. No real customer records or invented links to external datasets.
- Setup, credentials, resource names, log query and retention route: [cloud setup](../../docs/cloud-setup.md). Runtime uses a scoped service identity; no exported service-account keys.

Sources resolve through each run's pinned input hash. Original PDFs are hash-checked against extracted evidence. Numeric observations belong to deterministic tools; model prose is visibly an interpretation requiring human review. Review reasons are mandatory and saved once against an immutable report hash/version. Scoped reads reject another session; provider failure yields a visible error/gap without a canned model report.

## Cost evidence

`artifacts/budget-verification.json` verifies two monthly project-only budgets, excluding all credits: 750,000 VND (50/80/100%) and 950,000 VND (80/100%). Alerts do not shut down billing.

| Control | Implemented bound |
|---|---|
| Durable quota | 200 lifetime model-backed run reservations; five per anonymous session; retained on failures |
| Model | Per run: 50,000 conservative input-token bound, 8,000 maximum output tokens, 12 model calls and 20 tool calls |
| Document AI | 200 attempted one-page parses; hash/processor/normalization-version cache |
| BigQuery | Fixed parameterized queries, dry run, 20 MiB maximum/query and 500 rows |
| Cloud Run | One service/revision instance, minimum zero, one CPU/512 MiB, request billing, CPU boost disabled |
| Retention | Dedicated GCS objects and BigQuery tables expire after 30 days |

Worst model reservation is $4.90, Document AI $6, BigQuery reserve $0.10, Cloud Run reserve $5 and build/storage/registry/log reserve $5: approximately $21. At planning FX 30,000 VND/USD, approximately 630,000 VND; plus 30% reserve, approximately 820,000 VND. This forecast covers the prototype allowances, not unrelated workloads or unbounded public HTTP traffic. Free-credit eligibility and billed invoice totals are unverified.

Before final browser verification: 130 run reservations, 66 attempted pages and 70 remaining runs. Do not reset the ledger to bypass limits. The 90-run evaluation captured 199,493 input and 41,888 output tokens: approximately $0.113 at the published model prices for captured successful responses; retries/failures may add usage. This is not total billed project cost.

## Verification and measured limitations

- 17 focused Python tests pass; Ruff check/format and frontend TypeScript/build pass. Full npm audit reports zero vulnerabilities at verification. FastAPI TestClient reports a dependency deprecation warning; tests are not hidden or weakened.
- Five live scenarios passed local and earlier cloud browser verification, including inspection, review, reload persistence and rejected overwrite. Final revision browser verification includes pinned PDF downloads and preserving the previous readable report/key when the session quota rejects a new run; its result is recorded below after completion.
- 90 actual live ADK evaluations: 30 held-out-seed cases, three repetitions each; zero run errors and zero specialist gaps. All 90 report citation membership and source-scope checks pass. Median duration 42.02 s, p95 80.79 s and maximum 85.58 s. This mixed-traffic measurement is not a controlled warm/cold benchmark.
- Original indicator counts: TP 63, FP 9, FN 9. Frozen inputs intentionally plant an ownership declaration/document discrepancy that the original ownership gold labels omitted. Original results, truth and manifest hashes are retained. A separately disclosed construction rescore yields TP 72, FP 0, FN 9; precision 100%, recall 88.9%. This post-run correction is not an independent preregistered accuracy result.
- All nine remaining misses are three repeated positive document cases with required OCR fields below the 0.7 confidence threshold. Correct behavior is explicit unresolved status; the held-out document detection recall target is missed (0/9 positives). No threshold was lowered or extraction fabricated to improve the score.
- The earlier tools-only 50-case run yielded TP 37, FP 0, FN 3. Its generator/declaration state differs from the later live corpus; it is not a controlled claim of improvement from Gemini.
- Evaluation inputs/truth were frozen separately and excluded from images, upload source and runtime access. Seed/name/amount variation reuses template topology: independent topology-family holdout remains unimplemented. No real-world AML generalization or legal determination is claimed.
- The original evaluator computed its source hash from disk at finish; files changed during the batch while the process retained imported code. Exact loaded-source provenance is therefore incomplete. Future runs capture a source hash at start and finish. Existing measurements are preserved with this limitation.
- Citation membership is not semantic support. Independent human claim-support review, the proposed 95% gate, comprehensive adversarial document-injection tests, controlled cold starts and blocking-RPC deadline fault proof remain unverified. The async workflow budget is 120 s with bounded SDK calls; synchronous RPC time can delay cancellation.
- UI verification covered 375/768/1440 layouts and source-backed graph controls. Graph labels are dense on small screens; the accessible record list is available. Dedicated component and exhaustive automated accessibility suites remain unimplemented.

## Review, rollback and process cleanup

The scoped code review found and fixed stale current-case sources in historical reports, loss of the saved report/key on quota rejection, orphan polling after rejection and missing PDF integrity verification. Tests and live verification cover the affected source/review flow. Remaining research verification gaps above are explicit, not a clean all-gates claim.

Deployment log: `artifacts/deploy-final.log`; service settings: `artifacts/deployed-service.json`. List revisions before rollback. Previous pinned-source revision `casemind-ai-00005-vk4` exists; traffic command: `gcloud --configuration=casemind-ai run services update-traffic casemind-ai --region=asia-southeast1 --to-revisions=casemind-ai-00005-vk4=100`. No rollback was performed during final verification. Keep immutable artifacts and reservations; do not delete existing data.

Local development server was stopped. Benchmark processes completed; browser/build processes are reconciled at finish. The managed Cloud Run service remains available for the user. No GitHub repository, deck/video publication or competition submission was performed.

## Final browser verification

2026-10-10 local time: final revision live browser E2E passed in 5.8 minutes. All five cases, source records, all available original PDFs, immutable review/reload, overwrite rejection, responsive overflow checks and quota rejection preserving report/key passed. Log: `artifacts/e2e-release.log`.

Earlier failed test assumed screening had a PDF; the next test run was interrupted to correct the completed-report button selector. Logs and reservations remain retained. Local benchmark, build, browser and development processes completed or were stopped; no application listener remains on port 8080.

Final usage read: 139 reserved runs and 66 attempted pages; 61 run reservations remain. Budgets still exclude all credits. The final rejected quota attempt consumed no additional run reservation.
