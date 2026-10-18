# Investigator workspace

Implemented locally on 2026-10-11. The ten-feature workspace is an extension of
the five synthetic scenarios, within one FastAPI service and React application.
Local verification and pending live gates are recorded in the
[execution report](../plans/reports/cook-261011-1326-investigator-workspace.md).
The existing deployed prototype has not been updated by this implementation.

## Navigation and evidence

Select a case in the left sidebar. Watchlist is a visible tab beside Overview.
Its candidate preview works before investigation; a completed run enables
report-bound human candidate assessments. Name similarity, sanctions and PEP
indicators do not establish identity or criminality.

| Tab | Behavior |
|---|---|
| Sources | Search and inspect typed source records, with visible/total counts. |
| Watchlist | Supporting/conflicting identifiers, missing attributes and human assessment. |
| Findings | Tool facts, parameters, source references, coverage and limitations. |
| Transaction reasons | Explain a selected transaction's recorded rule, target/context role, supporting facts, alternatives and gaps. Uncollected tools remain not evaluated. |
| Money trail | Directed, chronological transactions with exact Decimal amounts and account/currency/direction/time display filters. A connected path does not prove fund identity. |
| Ownership | Ordered relationships, per-step percentages, exact path product, unknowns, cycles, depth and overlap warnings. No jurisdictional legal UBO conclusion. |
| Documents | Raw/normalized field comparison, extraction confidence, page/anchor lineage and inert PNG previews. Original PDFs download as attachments. |
| Follow-up | Persist notes/checks; authenticated investigators can supply new synthetic CSV/JSON/PDF, inspect quarantine, commit a child snapshot and explicitly execute a linked investigation. |
| Case Q&A | Ask within a completed pinned run. Exact values/reasons are deterministic; allowed interpretive questions use bounded cited Gemini synthesis. Unsupported questions abstain. |
| History | Browse the current/proven actor's runs, reopen pinned inputs and compare semantic changes. Lost-cookie runs without saved ownership proof are inaccessible. |

Overview retains the execution timeline, graph, report and human review. Report
controls retain JSON and add printable HTML and generated PDF. HTML/PDF share an
allowlisted export projection; neither exports an entire OCR document. Existing
JSON report bytes and hashes are unchanged. PDF uses packaged fonts; unsupported
glyphs return an explicit error, with HTML/JSON available.

## Insights, advisories and second review

Added locally on 2026-10-18 ([plan](../plans/261018-1536-workspace-insights-expansion/plan.md)).
These views read the pinned snapshot and recorded evidence. None of them writes to
an existing report, and report and review hashes do not change. Logic lives in
[insights.py](../backend/casemind/insights.py), [advisory.py](../backend/casemind/advisory.py)
and [insight_routes.py](../backend/casemind/insight_routes.py).

| Tab | Behavior |
|---|---|
| Triage | Latest completed run per case for the actor, ranked by the recorded triage policy, with review and second-check state. |
| Replay | Transfers in recorded time order on the graph, with the latest one highlighted. |
| Typologies | Recorded indicators mapped to demonstration typology categories as observed, evaluated but not observed, or not evaluated. |
| Challenge | Deterministic checks of one common legitimate explanation per indicator, "what would change the conclusion" ranked by triage weight, and an optional cited Gemini counter-argument. |
| What-if | Re-runs the transaction rules with investigator-supplied parameters and lists the transactions that would be added or removed. Nothing is persisted. |
| Graph query | Gemini proposes a bounded path query (at most four hops) that the investigator reviews. The query then runs deterministically. |
| RFI drafts | Gemini drafts neutral, editable requests from the change drivers. CaseMind never sends them. |
| Evaluation | Aggregate-only scorecard of the latest live and offline benchmark runs, plus the run history. |

Model-backed advisories reuse the bounded operation authority: idempotency key,
quota, a 120-second fenced deadline and one schema-constrained call. Prose must be
digit-free and cite pinned evidence IDs. Graph plans must name accounts or entities
in the case. Without configured Google Cloud, these calls fail explicitly; there is
no canned fallback.

The guided demo in the top bar walks through twelve steps. It never starts a billed
run. Reports offer a bilingual HTML export (`?lang=vi`): headings and labels are in
Vietnamese and English, while model prose and source facts stay in the original
English and are not machine-translated.

**Maker-checker.** Once the maker has recorded an immutable review, they can request
a check bound to the report hash. A different allowlisted, signed-in investigator
opens the check by ID, sees the export projection, and records an immutable
`concur` (four eyes confirmed) or `dispute` (escalated disagreement). The maker's
review is never overwritten, and the maker cannot check their own review.

**Embedded-instruction safety control.** A sixth demo case, labeled as a safety
control, carries KYB text that tries to direct the reviewer. The
`detect_embedded_instructions` tool flags it as a document-provenance indicator.
That indicator carries weight in triage policy version 2. Matching text is withheld
from every model-bound payload: specialist tool results, synthesis, Q&A and
advisories. The five requested scenarios and the benchmark corpus are unchanged.

Run `./.venv/bin/python scripts/build-evaluation-summary.py` after a new benchmark
run to refresh `backend/casemind/data/evaluation-summary.json`. Only counts and
rates are copied; per-case labels and private truth are never included.

## Source and snapshot contracts

The implemented schemas are authoritative in
[models.py](../backend/casemind/models.py). V1 snapshots validate the original raw
case hash before adaptation. V2 manifests hash their explicit case, owner,
parent identity, source objects and source metadata. Uploaded origin and
synthetic classification are separate fields. This release accepts supplied
synthetic data; personal/regulated production data is outside its scope.

[SourceCatalog](../backend/casemind/source_catalog.py) stores immutable originals
by hash, media type, size and generation. Imported PDF routes require those exact
bytes; they never substitute regenerated demo documents. PNG derivatives retain
original hash/generation/page lineage. PDF parsing runs in a disposable,
resource-bounded process: 50 pages, 16 million pixels per page, 128 MiB decoded
raster, 512 MiB RSS, 10 CPU seconds and 15 wall seconds. Oversized or malformed
inputs fail explicitly.

Analytics retrieve the complete snapshot up to 5,000 transactions. Evidence
version 2 records ordered transaction IDs, participant/context roles, anomaly
targets, coverage and document field lineage. Legacy evidence retains unknown
order or evaluation status. Display filters never silently recompute a finding.
Every inspector and question resolves through the selected case or pinned run.

## Restricted sign-in and new-data follow-up

Sign-in is disabled unless all three environment settings exist:

- `CASEMIND_GOOGLE_CLIENT_ID`: GIS web client audience for the intended origin.
- `CASEMIND_INVESTIGATOR_SUBJECTS`: comma-separated allowed Google subject IDs.
- `CASEMIND_SESSION_SECRET`: at least 32 characters, supplied through the runtime's secret route.

These settings are supported by the code; no OAuth resource or deployment was
configured in this session. Google authentication uses a same-origin JavaScript
callback, CSRF check, token verification and subject allowlist. Signed cookies
carry opaque session IDs; persisted expiry/revocation is checked on every
request. Sign-out revokes the server-side record. Sign-in claims only anonymous
runs whose capability proof exists before rotation. Login verification is
bounded to six attempts per session and sixty globally per minute.

Follow-up commands require an idempotency key and expected version. Intake uses
one raw, streamed file body per request, avoiding multipart buffering. The UI
supplies filename, media type, key and version to the intake route. Limits are
CSV 2 MiB/5,000 rows, JSON 1 MiB/1,000 records, PDF 10 MiB each, ten PDFs/fifty
pages and 64 MiB staged per follow-up. The general decoded request cap is 32 MiB.
Staging is temporary and has a one-hour cleanup sweep.

A versioned `IntakeBatch` joins typed records, add/supersede actions, target
revisions and original-object references. Whole-batch validation supports forward
references and preserves rejected records with reasons. Canonical ordering makes
structured-record permutations produce the same child identity. Original bytes
and provenance remain immutable. Commit never mutates the parent or its report;
execution creates a linked child run. Failed prepared commands can be explicitly
cancelled when no provider execution is active.

## Execution, recovery and Q&A

Ordinary and follow-up investigations use immutable operation request envelopes,
CAS state manifests, append-only events and idempotent quota/history projections.
Changed reuse of an idempotency key returns 409 before quota. Provider work starts
from confirmed ready state, within one absolute 120-second fenced deadline.
Publication records intent and deterministic BigQuery job identity, verifies full
row content and original object generations, then commits a table pointer.

History advances a persisted recovery cursor, repairs metadata and marks expired
execution interrupted. Recovery never retries provider work. An explicit new
attempt is required. Document AI reserves verified selected pages before each
actual attempt. Form Parser processes the same original PDF in selections of at
most fifteen pages, retaining original page numbers and remapping text anchors.
This respects the [Document AI synchronous limits](https://docs.cloud.google.com/document-ai/limits)
without changing original bytes. Failures/mismatches retain the reservation. Completed extraction
is cached by original hash, processor and extraction version.

Q&A reads one owned pinned report with bounded count/serialized retrieval. Exact
answers carry pinned source references and relevant recorded evidence IDs.
Interpretive answers permit one bounded synthesis call without tools, validate
citation membership and digit-free prose, and persist usage and results through
the same operation authority. Citation membership does not prove semantic support;
human review remains required.

## Local verification and remaining live gates

```bash
./.venv/bin/python -m pytest -q
./.venv/bin/python -m ruff check backend tests evaluation scripts
npm --prefix frontend run typecheck
npm --prefix frontend run build
PYTHONPATH=backend ./.venv/bin/python evaluation/run-evaluation.py --split all --repeats 1 --concurrency 1
npm --prefix frontend run test:e2e:offline
```

The offline browser harness starts real product routes on port 8081 (override with
`CASEMIND_OFFLINE_PORT`) with a throwaway store and test-only deterministic evidence.
It covers the five scenarios and every workspace tab at 375/768/1440 widths. Test seed routes and evaluator truth are excluded from the
container. The offline evaluator neither constructs Cloud nor reads credentials;
its synthetic extraction adapter does not measure OCR or model quality.

Release readiness still requires configured real GIS, GCS generations, Document
AI/Gemini/tool integration, semantic answer review and deployed authenticated
browser checks. Cloud configuration, spending, deployment and publication remain
separate authorized actions. Back up persistent state before any live migration;
restore backups or an explicitly recorded deployment revision for rollback.
