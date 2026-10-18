# Workspace, explorers and export implementation

Status: DONE_WITH_CONCERNS

## Delivered contracts

- `build_workspace(case, report=None, snapshot=None, limit=200)` returns a typed `WorkspaceView` with scope, counts, bounded sources/findings/screening candidates, coverage and hidden counts. Case-only screening is a deterministic preview; finding cards remain empty until a report exists. Unknown tools/versions retain raw payload and all refs.
- `validate_screening_assessment(case, report, request)` checks candidate IDs and report hash/version and returns a canonical request projection/hash. `ScreeningAssessmentRequest` owns request validation. Actor authorization, CAS, persistence, idempotency and owner-alias resolution remain integration-owner responsibilities.
- `build_money_trail(case, report=None, snapshot=None, account_id=..., currency=..., direction=..., limit=..., start=..., end=...)` keeps Decimal strings, chronological transaction order, source-derived participant roles and recorded ordered paths. Account/direction/currency/time filters disclose total/matched/visible/hidden counts without recomputing findings. Legacy order fallback is explicitly labeled `reconstructed_from_sources`.
- `build_ownership(case, report=None, snapshot=None, target_id=..., limit=...)` returns bounded ordered relationship steps, exact per-path products, declaration source and unknown/cycle/depth/overlap/missing-ownership flags. Cycles, excessive depth and unknown percentages return no confident product. Paths are never summed.
- `build_document_comparison(case, report, snapshot=None, document_id=..., limit=...)` exposes raw/normalized values, each field's document/page/anchor/confidence/geometry, pinned source object and evidence lineage. Comparisons retain evidence refs and link relevant extracted field values. Absent original/geometry metadata is explicit.
- Snapshot arguments accept `SnapshotRef` or metadata dictionaries. Projections validate report case/input hash, refs and supplemental transaction/document lineage before rendering.
- `build_export_view(case, report, snapshot=None, review=None)` checks report hash and pinned review binding. Frozen sections project readable synthesis plus authoritative report facts, source excerpts/identities/hashes, catalog metadata, review hash and offline limitations. `render_html(view)` returns escaped, self-contained, script-free HTML; `render_pdf(view)` uses the identical projection through escaped ReportLab text. Existing reports are never changed.

## Files

Only the delegated modules and tests were edited: `backend/casemind/workspace.py`, `explorers.py`, `exports.py`, `tests/test_workspace_api.py`, `test_explorers.py`, and `test_exports.py`.

## Validation

Focused modules plus existing analytics, v2 identity, provenance, timezone filters and PDF text extraction: **22 passed**. Scoped Ruff checks: **passed**.

Coverage includes preview versus completed findings, candidate hash/version mismatch, foreign refs/supplemental lineage, unknown renderer versions, bounded inventory, exact Decimal values, directional filters, traversal order, currency separation, ownership unknown percentages/cycles, document locator preservation, report immutability, HTML escaping, inert PDF output, report/hash parity and tampered/foreign export inputs.

## Integration concerns

- Route authentication, assessment persistence/CAS/owner migration, response headers and original PDF/page derivative endpoints are owned by the controller and foundation lane.
- Derivatives are not generated inside projection modules; document values carry the pinned original-object metadata for controller/UI integration.
- Export PDF uses ReportLab's packaged Vera.ttf with runtime glyph coverage validation. Unsupported codepoints fail explicitly with HTML/legacy JSON fallback; no substitute glyphs or font downloads are used.
- No cloud execution, spending, deployment, publication or background process was started.

Unresolved questions: none for these pure-module contracts.

## Final integration additions

Exports now include readable deterministic transaction reasons from the pinned reason builder with rule/evidence versions, parameters, observed values, ordered sources, alternatives and gaps. The linked-transaction display cap of 200 and hidden counts are explicit. Separate coverage sections retain each evidence identity/version. Source origin, nested structured source-object provenance, locators and original/derivative-page evidence lineage are carried into the same HTML/PDF view. Missing derivative refs remain explicitly unavailable offline. Tests extract actual PDF text with PDFium and verify shared readable facts/provenance/hashes against HTML.

Money-trail `from_timestamp` and `to_timestamp` display bounds accept only timezone-aware ISO timestamps. Reversed/naive bounds fail; filtering preserves recorded analysis paths.
