# Foundation implementation

Implemented Phase 1 backend foundation plus the controller-requested cloud execution/publication and offline evaluator extensions. Existing records retain the v1 `source_kind` contract. New snapshot/source metadata separates synthetic classification and generated/uploaded origin.

## Delivered contracts

- `SnapshotRef` carries immutable identity, adapted case, original raw v1 case, manifest version, source object references, metadata, owner and parent identity. `snapshot_from_manifest` verifies raw-v1 canonical identity before Pydantic adaptation; v2 identity covers the typed canonical manifest including original source references and ownership.
- `CaseResolver` resolves public demos for every actor and imported cases through an owner index. Imported PDFs require exact generation/hash-verified bytes. Missing uploaded originals have no regeneration fallback.
- File/GCS adapters provide binary immutable writes, exact generation reads, conditional staging write/delete and bounded JSON key scans. `SourceCatalog` handles content addressing and conditional staging promotion. Public staging primitives cannot overwrite immutable object keys.
- `pypdfium2==5.0.0` was installed and verified against valid, active-catalog, malformed, oversized-page and excessive-page fixtures. Parser runs in a disposable process with a 15-second wall limit, 10-second CPU limit, 512 MiB RSS watchdog, Linux address-space limit, 20-page / 16-million-pixel-per-page / 128-MiB decoded raster limits. Only PNG pixels escape; no forms, scripts, actions, attachments or network APIs are initialized. Linux uses `/proc`; macOS uses `ps`.
- Cloud boundaries require explicit snapshot identity and resolved bytes. Complete transaction retrieval is bounded at 5,000, deterministically ordered and canonically checked for missing, duplicate or changed rows. Setup and evaluator callers were migrated.
- Evidence semantics are version 2 and include explicit order, participation roles, anomaly targets, coverage and document field lineage. Reason generation is deterministic, distinguishes baseline context from anomaly targets and preserves legacy `not_evaluated`/unknown order states.
- Publication intent precedes BigQuery submission. Deterministic jobs are reconciled, table schema/count/content and original generations are verified before CAS publication of the table pointer. Execution fences bound each provider call and terminal write. Document AI reserves the actual verified page count atomically and retains reservations on failure/mismatch.
- Offline evaluation does not import/construct Cloud, load cloud configuration or call providers. It uses an explicitly labelled evaluator-only synthetic field adapter and records mode, configuration/source hashes and time; it does not claim to measure OCR quality. Ground truth stays in the evaluator's private output directory.

## Validation

`python -m pytest tests/test_evidence_foundation.py tests/test_evaluation_offline.py tests/test_contracts.py tests/test_analytics.py tests/test_store_api.py tests/test_reliability.py -q`: 30 passed (one existing Starlette/httpx deprecation warning).

`python -m ruff check backend/casemind tests evaluation scripts/setup-cloud.py`: passed.

The tests cover 500/501/5,000 complete transaction sets, 5,001 rejection, equal timestamp ordering, duplicate-content rejection, expired execution, crash-after-job publication reconciliation, reservation retention, owner scope, raw legacy identity despite missing optional defaults, staging generation conflicts, inert derivatives and a provider-disabled 50-case offline run.

## Integration

Main routes must retain `SnapshotRef` until source/cloud/run boundaries and return `snapshot.case` only for current case responses. Use `snapshot_from_manifest` for run-pinned sources, `resolver.document_bytes` for PDFs, `load_case(snapshot, documents, execution=None)` and `investigate(snapshot, run_id, store, cloud, emit, documents=None, execution=None)`. The controller owns and has implemented this wiring.

## Remaining gates

No cloud spending, deployment, provider integration calls or persistent-data migration was performed. Live GCS generation behavior, BigQuery job reconciliation, Document AI and Gemini integration remain live acceptance gates. Synthetic fixture extraction is an offline analytics adapter, not an OCR benchmark. Existing persisted artifact bytes were not rewritten by this worker; only temporary pytest stores were used.

## Fifty-page Document AI original support

The controller raised original preflight and attempt-reservation ceilings to 50 pages. Cloud extraction now respects Form Parser's online limit by selecting at most 15 pages per synchronous `ProcessRequest`, using `ProcessOptions.IndividualPageSelector` from pinned `google-cloud-documentai==3.16.0`. Every call sends the same verified original PDF bytes; no splitting or reconstruction occurs. The actual selected page count is reserved atomically immediately before each attempt, provider retries remain disabled, and execution checks bound each call and prevent stale cache publication.

Official references checked: [Document AI limits](https://docs.cloud.google.com/document-ai/limits) and [v1 ProcessOptions page-range semantics](https://docs.cloud.google.com/document-ai/docs/reference/rpc/google.cloud.documentai.v1). Form Parser supports 15 online pages; selection indices are one-based and returned `Document.Page.page_number` refers to the original page. The implementation does not depend on the separate imageless-mode extension.

Batch responses must contain exactly the requested original page numbers. Extracted field anchors and all serialized OCR text anchors are shifted into combined OCR text. Full OCR batch artifacts retain provider page layouts, tokens, forms, entities and metadata, with page references mapped into original-page indices. Each batch records its selection, text offset/length and aggregate-anchor space. A new cache version excludes earlier unbatched artifacts.

Verification: 22 foundation tests pass, including a real pinned-SDK synthetic 50-page fixture proving 15/15/15/5 calls, exact original bytes and selection coverage, combined field/text/page lineage, total 50-page reservation and cache replay without further calls. Provider failure, returned-count mismatch and returned-page-identity mismatch preserve 30 attempted pages and publish no partial cache. Quota exhaustion and expired execution stop subsequent calls. Cloud/foundation lint passed; broader foundation/analytics/contracts/reliability tests passed (34 tests). No live provider calls or spending occurred.
