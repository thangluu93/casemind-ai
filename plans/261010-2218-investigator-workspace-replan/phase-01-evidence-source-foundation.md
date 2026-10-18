---
phase: 1
title: "Evidence and source foundation"
status: completed
priority: P1
effort: "24-32 person-hours"
dependencies: []
---

# Phase 1: Evidence and source foundation

## Goal

Freeze additive contracts for immutable source bytes, case/run resolution, evidence attribution, order and legacy compatibility so every later feature consumes one pinned source model.

## Verified context

- `CASES = demo_cases()` and `case_or_404` resolve only generated cases; current case/source/document/start routes depend on it (`backend/casemind/main.py:19,69-72,152-203`).
- `pinned_case` parses a stored manifest and then recomputes `digest(case)` (`backend/casemind/main.py:96-108`). Optional model fields would change `model_dump` and can therefore break legacy hashes even if stored bytes never changed.
- Snapshot digest callers are `pinned_case`, run start, `Cloud.load_case`, `Cloud.query_transactions`, the report `input_hash`, and evaluator runtime-input freezes (`backend/casemind/main.py:96-108,192-240`; `backend/casemind/cloud.py:54-57,99-105`; `backend/casemind/investigation.py:324-347`; `evaluation/run-evaluation.py:88-117`). All must share versioned identity semantics.
- Cloud setup also calls `load_case`, `query_transactions` and `extract` directly (`scripts/setup-cloud.py:38-41`); it must migrate in the same boundary change rather than retain a parallel Case-only path.
- `Store` exposes only JSON `get`/`put`; File/GCS adapters provide CAS (`backend/casemind/store.py:14-97`). Complete legacy history needs a bounded primitive, never authorization by object-name guessing.
- Cloud loading and extraction generate PDFs from metadata (`backend/casemind/cloud.py:54-95,128-146`). That is valid for demos only; imported originals would otherwise be replaced.
- Live transaction retrieval is ordered but capped at 500 and rejects any result count different from the case (`backend/casemind/cloud.py:99-126`). Accepted parent-plus-intake snapshots must instead return the complete set through the 5,000-record ceiling.
- Evidence refs are sorted/deduplicated and cannot encode path order (`backend/casemind/analytics.py:9-30`). Activity evidence identifies a target but references baseline rows (`backend/casemind/analytics.py:166-194`).

## Contracts and data flow

1. Add source metadata with separate `classification` (`synthetic` now) and `origin` (`generated` or `uploaded` now). Legacy `source_kind: synthetic` remains the v1 decode/serialization contract; future public categories require real schema semantics and evidence.
2. Define `SourceObjectRef {sha256, media_type, byte_size, generation, storage_key}`. `put_blob_if_absent` verifies identical bytes on conflict; `get_blob` returns exact bytes/generation. Add generation-conditional temporary staging write/promote/delete plus bounded `scan_keys(prefix,cursor,limit)` for intake cleanup/bootstrap; scans never grant authorization.
3. Define a versioned `CaseManifest`. For v1, verify the raw stored `manifest["case"]` canonical JSON hash before Pydantic adaptation and retain its original snapshot ID through source retrieval, BigQuery table lookup, extraction and report creation. For v2, hash an explicit canonical manifest including source refs and parent identity. Never recompute a legacy identity from an expanded model dump.
4. Define minimal `ActorRef {kind, owner_id}` plus versioned owner-alias/claim lookup. All new owner-bound artifacts resolve this identity. Claims add separate authority mappings for old immutable reviews/runs; they never rewrite those artifacts.
5. `CaseResolver.resolve(case_id, actor)` returns public `CASES` to anonymous and authenticated actors, or an owner-indexed imported manifest only to its verified owner. Imported IDs never appear in the public namespace/list.
6. Resolve document bytes explicitly: demo refs may call `document_pdf`; imported refs load the exact object generation and verify SHA-256. `Cloud.load_case` and `Cloud.extract` accept resolved bytes instead of regenerating them.
7. Pin verified `pypdfium2` and expose one document preflight/derivative helper: verify media signature/page count under time, page, pixel and decompressed-byte caps; rasterize inert PNG pages without scripts/actions/attachments/network; hash each derivative and retain original hash/generation/page lineage. It never mutates the original.
8. Define a v2 maximum of 5,000 total transactions including inherited parent rows. `Cloud.query_transactions` retrieves the entire pinned set in deterministic `(timestamp,id)` order with exact expected count and canonical content hash; reject 5,001 before publication. Use one bounded 5,000-row query unless an integration check proves pagination necessary.
9. Add `ordered_transaction_ids`, `participant_roles`, `target_transaction_id`, field-level document lineage and coverage. `build_transaction_reasons(snapshot,evidence,transaction_id)` returns observed facts, rule/version/parameters, role, alternatives and gaps without a model. Legacy evidence without roles/order stays `order_unknown`/`not_evaluated`.

## Files and ownership

| Action | Absolute path | Owner/change |
|---|---|---|
| Modify | `/Users/thangluu/Repos/casemind-ai/backend/casemind/models.py` | Integration owner: ActorRef, additive manifest/source/lineage/reason schemas and v1 adapters. |
| Modify | `/Users/thangluu/Repos/casemind-ai/backend/casemind/store.py` | Foundation backend: immutable blobs, conditional temp staging lifecycle and bounded key scan for File/GCS. |
| Create | `/Users/thangluu/Repos/casemind-ai/backend/casemind/source_catalog.py` | Foundation backend: content addressing, byte verification and temp-to-immutable promotion. |
| Create | `/Users/thangluu/Repos/casemind-ai/backend/casemind/document_rendering.py` | Foundation backend: bounded PDF preflight and inert PNG derivatives with original lineage. |
| Create | `/Users/thangluu/Repos/casemind-ai/backend/casemind/case_resolver.py` | Foundation backend: versioned hashes and public/owned resolution. |
| Modify | `/Users/thangluu/Repos/casemind-ai/backend/casemind/cloud.py` | Foundation backend: explicit snapshot identity and resolved PDF bytes. |
| Modify | `/Users/thangluu/Repos/casemind-ai/backend/casemind/analytics.py` | Analytics owner: order, roles, coverage and document lineage. |
| Create | `/Users/thangluu/Repos/casemind-ai/backend/casemind/explanations.py` | Analytics owner: deterministic reason builder. |
| Modify | `/Users/thangluu/Repos/casemind-ai/backend/casemind/investigation.py` | Integration owner: preserve supplied snapshot ID in report input hash. |
| Modify | `/Users/thangluu/Repos/casemind-ai/backend/casemind/main.py` | Integration owner: replace direct `CASES` access through resolver. |
| Modify | `/Users/thangluu/Repos/casemind-ai/evaluation/run-evaluation.py` | Foundation integration owner: migrate runtime manifest/live investigation/query/extraction calls to SnapshotRef/resolved sources; offline/live separation remains Phase 6. |
| Modify | `/Users/thangluu/Repos/casemind-ai/scripts/setup-cloud.py` | Foundation integration owner: migrate load/query/extraction verification to SnapshotRef/resolved sources. |
| Modify | `/Users/thangluu/Repos/casemind-ai/pyproject.toml` | Integration owner: pin `pypdfium2` only after active/malformed fixture verification. |
| Modify | `/Users/thangluu/Repos/casemind-ai/tests/test_contracts.py` | Golden v1 bytes/digests and v2 canonical hashing. |
| Modify | `/Users/thangluu/Repos/casemind-ai/tests/test_analytics.py` | Attribution/order/coverage/reason controls. |
| Modify | `/Users/thangluu/Repos/casemind-ai/tests/test_store_api.py` | Blob generation, resolver scope and bounded scan. |
| Modify | `/Users/thangluu/Repos/casemind-ai/tests/test_reliability.py` | Original PDF and pinned identity integrity. |

## Implementation steps

1. Capture byte-level golden fixtures for current manifests, evidence, reports and reviews without normalizing key/list order. Back up persistent data and checksums before migration tests; old list position is never treated as semantic identity.
2. Implement raw-v1 canonical verification and v2 manifest hashing first. Make `SnapshotRef` plus resolved sources the required boundary for Cloud/investigation. Migrate main, `scripts/setup-cloud.py`, and every evaluator runtime manifest/live investigation/query/extraction caller in this phase; add a regression that optional defaults cannot change a v1 ID.
3. Add `ActorRef` and owner-alias resolution before Phase 2. New artifact ownership uses aliases; legacy runs/reviews retain bytes and gain authority only through a separate verified mapping.
4. Add blob/temp methods to both store adapters. Validate key, digest, size, media type and generation; identical immutable writes are idempotent, differing bytes conflict, promotion is conditional and abandoned temp objects are deletable by generation/TTL.
5. Implement resolver and replace all direct `CASES` reads through one helper. Preserve demo list/detail/source/PDF behavior for anonymous and signed-in actors; require verified ownership only for imported manifests.
6. Split demo PDF generation from byte resolution. Verify/pin `pypdfium2`; implement bounded preflight and content-addressed inert PNG rendering for any resolved demo/catalog original. Imported missing/mismatched objects fail closed; no regeneration fallback.
7. Raise the bounded full-set query contract to 5,000, verify exact count/content hash/order, and prove 500, 501 and 5,000 plus equal-timestamp/page-boundary controls. Parent+new total 5,001 is rejected.
8. Extend analytics at computation sites and implement every reason/negative state while preserving or explicitly versioning evidence semantics.

## Verification

```bash
./.venv/bin/python -m pytest tests/test_contracts.py tests/test_analytics.py tests/test_store_api.py tests/test_reliability.py -q
./.venv/bin/python -m ruff check backend/casemind tests evaluation scripts/setup-cloud.py
```

Gates: old bytes/hashes match; caller search finds no direct legacy Case-only boundary; evaluator/setup use SnapshotRef/resolved sources; ActorRef aliases do not rewrite artifacts; 500/501/5,000 rows reach analytics and 5,001 fails; PDFs round-trip; active/malformed/decompression fixtures yield bounded inert derivatives or explicit failure; public/imported scope and reasons stay correct.

## Risks and rollback

| Risk | Likelihood × impact | Mitigation |
|---|---|---|
| Model defaults change legacy hashes | High × High | Raw canonical v1 verification, threaded snapshot ref and golden callers test. |
| File/GCS blob behavior diverges | Medium × High | Adapter contract tests plus live GCS gate in Phase 6. |
| Context rows inherit suspicion | High × High | Explicit roles/targets and negative controls. |
| Resolver exposes imported cases | Medium × High | Owner index before imported manifest; public `CASES` namespace is available to all actors. |
| PDF derivative executes active content or exhausts resources | Medium × High | Verified pinned renderer, hard preflight/render caps, inert PNG output and hostile fixtures. |

Rollback disables v2 routes and restores the explicit data backup. Keep immutable new objects for audit; never rewrite old artifacts.

## Done

- [x] Old artifact bytes and all v1 snapshot callers remain compatible.
- [x] Originals and structured sources are content addressed and generation verified.
- [x] One bounded preflight/inert-derivative contract serves demo and uploaded PDFs without changing originals.
- [x] Public versus owner-bound resolution is explicit and tested.
- [x] ActorRef/owner aliases are available to every later owner-bound artifact without mutating legacy data.
- [x] The complete deterministically ordered transaction set reaches analytics through the 5,000 total-record ceiling.
- [x] Reason order, roles, coverage and legacy-unknown states are deterministic.

## Execution evidence

Completed locally on 2026-10-11. See the [execution report](../reports/cook-261011-1326-investigator-workspace.md)
and [independent review](../reports/code-review-261011-workspace.md).
Provider behavior and deployed authentication remain Phase 6 live gates.
