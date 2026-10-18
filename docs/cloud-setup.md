# Cloud setup and cost policy

Project `casemind-ai`, number `251896792352`; region `asia-southeast1`.
Resources are dedicated to this synthetic prototype. No service-account keys.

## Commands

Use the project's prepared Python environment with dependencies from
[pyproject.toml](../pyproject.toml). Build the UI with `npm --prefix frontend ci`
and `npm --prefix frontend run build`. With `CASEMIND_USE_GCLOUD=true`, run
`scripts/setup-cloud.py` and `scripts/configure-runtime.py` using that interpreter.
Deploy with `sh scripts/deploy-cloud-run.sh`.

`setup-cloud.py` writes non-secret resource names to `artifacts/cloud-config.json`.
For local live use, set `CASEMIND_CLOUD=true`, `CASEMIND_USE_GCLOUD=true` and
`CASEMIND_PROCESSOR` to that processor name; start `uvicorn casemind.main:app
--host 127.0.0.1 --port 8080`. No simulated model fallback.
Without cloud configuration, the UI and source records work; new runs return 503.

## Operational route

- Service: `casemind-ai`; canonical URL from `gcloud --configuration=casemind-ai run services describe casemind-ai --region=asia-southeast1 --format='value(status.url)'`.
- Health: `/api/health`; workspace `/`; case inventory `/api/cases`.
- Bucket: `casemind-ai-prototype-251896792352`; dataset: `casemind_prototype_v1`.
- Processor: `projects/251896792352/locations/asia-southeast1/processors/98ee587f2607fb39`.
- Model: global `gemini-3.1-flash-lite`; Google ADK 2.11.0.
- Logs: `gcloud --configuration=casemind-ai logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="casemind-ai"' --limit=20`.
- Rollback: list revisions, then `gcloud --configuration=casemind-ai run services update-traffic casemind-ai --region=asia-southeast1 --to-revisions=VERIFIED_REVISION=100`.
- IAM: runtime reads only the dedicated BigQuery dataset, writes dedicated bucket artifacts, calls Vertex/Document AI and runs bounded query jobs. Evaluator truth stays local and is excluded from cloud builds/images.

Reports resolve sources through the pinned input hash and run-scoped source routes.
Sources and reports are immutable application objects. GCS generation preconditions
protect concurrent writes; reviews are appended once per report version. Events
survive restart; abandoned runs become interrupted, with an explicit new attempt.
The local FileStore supports one process; production requires GCS.

## Cost controls and estimate

The latest limit is gross service cost below **1,000,000 VND**, regardless of credits.
Monthly budgets scoped to this project: 750,000 VND at 50/80/100%, and 950,000 VND
at 80/100%; both exclude credits. These send alerts, not automatic shutdowns.
The quota is lifetime for this prototype version, not reset on each deployment.

| Service | Bounded allowance / planning estimate |
|---|---|
| Gemini | 200 runs; each reserves at most 50,000 input and 8,000 output tokens. At $0.25/$1.50 per million, worst reservation about $4.90 |
| Document AI Form Parser | 200 attempted pages, including uncertain failures; $30/1,000 pages gives $6; hash/processor/version cache avoids repeat parsing |
| BigQuery | 20 MiB/query cap, fixed scoped templates, complete pinned snapshots up to 5,000 rows; reserve $0.10 |
| Cloud Run | One service and one revision instance, minimum zero, request billing, 512 MiB, one CPU; reserve $5 for prototype/demo traffic |
| Build, registry, storage, logs | Reserve $5; small synthetic objects, 30-day source retention |

Total planning reserve about $21.00: about **630,000 VND** at a deliberately
conservative planning conversion of 30,000 VND/USD. Keeping another 30% for tax,
SKU currency differences and incidental usage gives approximately **820,000 VND**.
This is an estimate, not an invoice or a provider-enforced hard spending limit.
Other workloads and unusually high public HTTP traffic are outside these allowances.

[Gemini pricing](https://cloud.google.com/vertex-ai/generative-ai/pricing) and
[Document AI pricing](https://cloud.google.com/products/document-ai/pricing) are the
price sources. Prices, tax and billing-currency SKU charges can change. Stop new
runs if the usage ledger is exhausted; existing reports remain readable. Do not
reset usage state to bypass limits. Review Cloud Billing before raising any cap. Read current reservations and gross
budget configuration with `CASEMIND_USE_GCLOUD=true python scripts/check-cost-controls.py`
using the prepared interpreter. Its output is a usage reservation count, not billed spend.

## Workspace extension configuration

The locally implemented restricted sign-in settings and recovery/intake contracts
are listed in [investigator workspace](investigator-workspace.md). No GIS audience,
subject allowlist or signing secret was configured or deployed by the October 11
workspace session. Keep auth disabled until those settings are supplied through
the authorized runtime route. Existing live resource names above describe the
earlier prototype, not verification of the workspace extension.
