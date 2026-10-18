# Research findings

Checked 2026-10-09, Asia/Ho_Chi_Minh. Findings are based on primary public
documentation. No dataset archive was downloaded, no cloud account was inspected,
and no service or framework was installed or executed. Published availability
is evidence of a route, not proof that this project has access or quota.

## Dataset decisions

| Source | Published access and license | Practical fit and decision |
|---|---|---|
| [IBM AML-Data](https://github.com/IBM/AML-Data/blob/main/README.md) | CSV through linked Kaggle and Box routes. Repository Apache-2.0; actual data CDLA-Sharing-1.0. Generated synthetic transactions include laundering tags. | Primary external transaction benchmark. Download a bounded sample, inspect actual schema and archive terms before ingestion. Keep labels outside investigator inputs; transaction tags alone do not define complete case narratives. |
| [IBM AMLSim](https://github.com/IBM/AMLSim) | Apache-2.0 repository with generator and sample outputs. README recommends master; dependencies include Java 8, Python 3.7 and old NetworkX. | Useful pattern reference and optional external benchmark. Do not make its legacy environment a dependency of the nine-day build. Verify generated-output terms separately before distribution. |
| [OpenSanctions](https://www.opensanctions.org/docs/commercial/exemption/) | Bulk database is CC BY-NC 4.0 for noncommercial use. Commercial business use needs a data license; API free access has separate conditions. | Useful sanctions/PEP adapter; intended competition use has not been cleared. Public prototype uses clearly synthetic watchlist records, with real matching logic. This is a licensing boundary, not a claim of real screening coverage. |
| [GLEIF](https://www.gleif.org/en/meta/lei-data-terms-of-use/) | LEI reference data under CC0, subject to access terms. [API](https://www.gleif.org/en/lei-data/gleif-api) supports search, field filters and fuzzy matching; bulk files are another route. | Best candidate for real public entity enrichment. Use a small versioned snapshot and preserve source IDs. Real records remain outside synthetic crime cases. |
| [ICIJ Offshore Leaks](https://offshoreleaks.icij.org/pages/database) | Downloadable node/relationship CSV archives and Neo4j dumps. Database ODbL; contents CC BY-SA; attribution required. | Relationship-data research and separate optional explorer. Do not bundle into synthetic financial-crime stories or require a Neo4j deployment for the prototype. |
| [Document AI samples](https://github.com/GoogleCloudPlatform/document-ai-samples) | Apache-2.0 code samples; README points to public `gs://cloud-samples-data/documentai/` documents and processor sample outputs. | Integration examples, not a ready KYC benchmark. Check individual asset terms before redistribution. Generate visibly synthetic KYC/KYB PDFs for the actual cases. |

These sources do not establish a common identity key. In particular,
[GLEIF Level 2](https://www.gleif.org/en/lei-data/access-and-use-lei-data/level-2-data-who-owns-whom)
describes direct and ultimate accounting-consolidating parents. That is not a
complete natural-person beneficial ownership register. Missing parent data and
reporting exceptions must remain unknown, rather than inferred ownership.

The [ICIJ explanation](https://offshoreleaks.icij.org/pages/about) provides
historical context for the database. Presence in that dataset is not a risk
finding by itself, and the project must not treat it as evidence of illegality.

## Access verification before implementation

For every imported snapshot record source URL, retrieval time, source version,
license, redistribution decision, schema version and SHA-256. Check one sample
record before bulk ingestion. Test currency fields, timestamps, labels and nulls.
Do not commit external archives, labels or third-party records automatically.

IBM account identifiers must be namespaced with their bank/source identifiers.
Do not assume a bare account string is globally unique. Do not combine currency
amounts without an explicit exchange-rate source and timestamp. The exact IBM
headers and row counts remain unverified until an archive is acquired.

Use IBM as the primary external transaction evaluation source. Use an independent
seeded CaseMind generator for integrated transaction/entity/document cases.
Do not claim IBM ground truth validates invented ownership or KYC relationships.

## Framework comparison

| Option | Verified capability | Assumption and earliest failure | Decision |
|---|---|---|---|
| [Google ADK](https://adk.dev/workflows/) | Multi-agent and graph workflows; [Cloud Run deployment](https://adk.dev/deploy/cloud-run/); [Gemini integration](https://adk.dev/agents/models/google-gemini/) | Python integration and typed evidence fit the selected stable release; fails if model/tool/state behavior cannot be reproduced quickly | Recommended for specialist coordination; application owns approval and durable evidence |
| [LangGraph](https://docs.langchain.com/oss/python/langgraph/overview) | Durable execution, streaming, human input and mixed deterministic/model steps | Team can configure persistence and model integration; fails when the additional orchestration choices slow delivery | Strong alternative if resumable long investigations become the primary need |
| Direct Google Gen AI SDK | [Function calling](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/multimodal/function-calling) and [structured output](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/multimodal/control-generated-output) | Team maintains its own bounded execution loop; fails when orchestration and tracing become bespoke framework work | Thin fallback runtime only if ADK integration is blocked; retain all domain contracts |

No framework performance ranking was measured. Pin a tested ADK release and
model identifier after one tool-call and structured-output integration check.
Current ADK documentation has moved to `adk.dev`; older examples require version
verification. Frameworks do not automatically make findings evidence-backed.

## Google Cloud service choices

| Component | Prototype role | Constraint and verification |
|---|---|---|
| Gemini on Vertex AI / current Google model platform | Planning, specialist interpretation, competing hypotheses and report synthesis | Function calls describe requests; the application executes and validates them. JSON schemas constrain syntax, not factual truth. Verify model access and region in the chosen project. |
| Cloud Run | One Python API/ADK container serving a built React UI | [Runtime contract](https://docs.cloud.google.com/run/docs/container-contract) makes local storage unsuitable for durable state. Run work within bounded requests; retain checkpoints externally. |
| BigQuery | Immutable transaction/entity snapshots and parameterized analytic queries | Use partition filters, bounded row results, dry runs and maximum bytes billed. [Cost guidance](https://docs.cloud.google.com/bigquery/docs/best-practices-costs) explains query controls. Never grant the model arbitrary SQL execution. |
| Document AI Form Parser | Extract document text, key/value pairs and tables before normalization | [Processor list](https://docs.cloud.google.com/document-ai/docs/processors-list) documents processor versions, regions and page limits. Validate the chosen processor on synthetic forms; do not assume legal-document authenticity detection. |
| Cloud Storage | Original case documents, versioned bundles, evidence/results and reviews | Use private objects and generation preconditions for writes; [preconditions](https://docs.cloud.google.com/storage/docs/request-preconditions) support conflict detection. Object access must be mediated by the API. |
| Cloud Logging | Structured execution events and operational failures | Record tool arguments after redaction, source IDs, durations and versions. Case reports live in Storage, not only logs. |
| Cloud SQL / AlloyDB | Later relational case workflow and multi-user review | Not needed for bounded case artifacts. If introduced, back up before migrations or data mutation; [Cloud SQL backups](https://docs.cloud.google.com/sql/docs/postgres/backup-recovery/backups) describe managed recovery. |
| Pub/Sub | Later durable asynchronous ingestion/orchestration | Add only when workload outlives requests and replay/idempotency requirements justify a queue. |
| Vertex AI Search / Agent Search | Later retrieval across a large authorized document corpus | Exact lookup by evidence ID is sufficient for five cases. Search results would still require source/page provenance and case access controls. |

Candidate default model: `gemini-3.5-flash`, subject to a real project smoke test.
The [current lifecycle table](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/model-versions)
lists availability through May 19, 2027 or later. It lists Gemini 2.5 retirement
on October 20, 2026, close to submission. Prefer the longer-lived candidate;
record the actual selected model and rerun evaluation on any change.

## Feasibility and cost

The user has no cloud project yet and plans to use at most $300 in GCP trial
credit. The [Free Trial documentation](https://docs.cloud.google.com/free/docs/free-cloud-features)
describes $300 for eligible new users over 90 days, with service restrictions.
This is separate from competition credits. Trial credit cannot pay for the
Gemini API in AI Studio or managed partner-model APIs. Use Google Gemini through
the cloud model platform, verify trial access, and do not assume a paid upgrade.

Proposed allocation: $100 for Gemini, $20 for document parsing, $30 for other
cloud services and $150 uncommitted reserve. These are ceilings, not estimates.
At the published [standard global Gemini 3.5 Flash rates](https://cloud.google.com/vertex-ai/generative-ai/pricing)
of $1.50 per million input tokens and $9 per million output tokens, an assumed
80,000 input plus 10,000 output tokens across an entire run costs $0.21;
200 such runs cost $42. Reasoning tokens count toward output. Regional rates,
retries and larger contexts alter this estimate. Record actual usage after
the first five runs and recompute the forecast.

[Form Parser pricing](https://cloud.google.com/document-ai/pricing) gives
$30 per 1,000 pages at the starting tier: 200 pages would cost $6. Cache extraction
by document hash and processor version; show that provenance and execute at least
one fresh extraction during integration verification. Account separately for
BigQuery bytes, compute, storage, builds, image retention, networking and logging.

Enforce cumulative run/token/page quotas in shared durable state and query limits;
a billing alert alone is not a spending cap. Target an initial maximum of 200
model-backed runs, 120,000 input and 20,000 output tokens per run, with the token
budget checked before each model call. Pause new runs on the application spend
threshold while leaving completed results readable. These controls reduce usage;
they do not cap every possible cloud charge. Deployment latency and total cost
remain unmeasured. Small preloaded cases reduce variance without prewriting results.

Next: activate and verify the trial/project; verify IBM download and schema;
test one Gemini tool call, one document parse and one bounded query; then lock
dependency versions and implement the contracts below.

## Unresolved questions

- Dataset archive access and redistribution obligations have not been tested.
- Competition-demo use of OpenSanctions needs license clarification.
- Trial eligibility, cloud permissions, quota and region compatibility are unknown.
