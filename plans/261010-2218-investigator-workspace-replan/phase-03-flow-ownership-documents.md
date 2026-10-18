---
phase: 3
title: "Flow, ownership and documents"
status: completed
priority: P1
effort: "28-40 person-hours"
dependencies: [2]
---

# Phase 3: Flow, ownership and documents

## Goal

Deliver interactive money trails, ownership derivations and original-document comparison using the Phase 1 lineage contracts and Phase 2 shared scope/inspector.

## Verified context

- The graph consumes raw transactions and formats amounts through JavaScript `Number`, risking loss of exact Decimal presentation (`frontend/src/flow-graph.tsx:4-29`).
- Analytics computes transaction, ownership and document evidence, but sorted refs lose traversal order and cross-document mismatches lose each value’s page/anchor lineage (`backend/casemind/analytics.py:197-203,210-311,432-446`).
- Run PDF verification can fall back to regenerated demo bytes (`backend/casemind/main.py:121-145`). Phase 1 forbids that fallback for imported originals.

## Contracts and data flow

1. Money trail receives ordered transaction IDs, Decimal strings, currency, direction, timestamps, participant roles and coverage. Display filters do not recompute findings; changed analysis bounds create a new recorded artifact.
2. Ownership response contains ordered relationship IDs, per-step percentages, derived product, unknown/cycle/depth/overlap flags and declaration evidence. It does not sum overlapping paths or claim jurisdictional UBO status.
3. Document comparison carries raw/normalized values plus `{document_id, source_object, page, text_anchor, confidence}` for each side. Optional geometry is used only when supplied; otherwise show page and escaped excerpt.
4. Original PDF routes are attachment-only with a conservative filename, `nosniff`, and response CSP `sandbox; default-src 'none'`; originals are never embedded or mutated. In-workspace comparison consumes Phase 1’s separately hashed inert PNG page derivatives and retains original hash/generation/page lineage.

## Files and ownership

| Action | Absolute path | Owner/change |
|---|---|---|
| Create | `/Users/thangluu/Repos/casemind-ai/backend/casemind/explorers.py` | Backend lane: bounded flow, ownership and document view models. |
| Modify | `/Users/thangluu/Repos/casemind-ai/backend/casemind/main.py` | Integration owner: explorer and verified PDF routes. |
| Create | `/Users/thangluu/Repos/casemind-ai/tests/test_explorers.py` | Backend lane: order, Decimal, ownership and locator tests. |
| Modify | `/Users/thangluu/Repos/casemind-ai/frontend/src/api.ts` | Integration owner: explorer/binary PDF contracts. |
| Modify | `/Users/thangluu/Repos/casemind-ai/frontend/src/flow-graph.tsx` | UI lane: filters, ordered list, reasons, exact values, keyboard. |
| Create | `/Users/thangluu/Repos/casemind-ai/frontend/src/ownership-explorer.tsx` | UI lane: path graph/table and derivations. |
| Create | `/Users/thangluu/Repos/casemind-ai/frontend/src/document-comparison.tsx` | UI lane: responsive comparison and anchor fallback. |
| Modify | `/Users/thangluu/Repos/casemind-ai/frontend/src/main.tsx` | Integration owner: compose views. |
| Modify | `/Users/thangluu/Repos/casemind-ai/frontend/src/styles.css` | Integration owner: responsive layouts. |

## Implementation steps

1. Build explorer models only from the selected snapshot; reject foreign evidence/path/document IDs.
2. Preserve order and exact strings; add display keys for parallel edges without changing source IDs.
3. Add bounded account, direction, currency and time display filters with visible/total counts. Never combine currencies without a supplied conversion artifact.
4. Coordinate graph and chronological list with the shared inspector; every visual edge is keyboard reachable in the list.
5. Show ownership step calculations and limitations independently. Null, cycles, depth and overlap never yield confident combined ownership.
6. Preserve extraction lineage through comparison. Show raw/normalized values and confidence.
7. Keep original download attachment-only. Resolve or generate Phase 1 inert page derivatives from demo/catalog bytes independently of intake, cache them content-addressed, and render only those images in workspace. Side-by-side desktop and sequential mobile layouts use page/excerpt fallback when a derivative/geometry is unavailable.

## Verification

```bash
./.venv/bin/python -m pytest tests/test_explorers.py tests/test_analytics.py tests/test_reliability.py -q
./.venv/bin/python -m ruff check backend/casemind/explorers.py backend/casemind/main.py tests/test_explorers.py
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

Gates: direction/order match sources; Decimal strings round-trip; currencies stay separate; ownership limitations persist; each value opens the correct inert page/fallback; original hash matches; active-PDF fixtures never execute in the application origin.

## Risks and rollback

| Risk | Likelihood × impact | Mitigation |
|---|---|---|
| Path implies unsupported fund identity | High × High | Roles/coverage labels and legitimate alternatives. |
| Ownership double-counts overlap | Medium × High | Independent paths; no unproven aggregation. |
| Viewer suggests false precision | Medium × High | Exact geometry or explicit page/excerpt fallback. |
| Browser retains stale PDF | Low × High | Scoped API and revoked object URLs. |
| Preserved PDF contains active content | Medium × High | Attachment-only original plus resource-bounded inert PNG derivative and active-content fixtures. |

Rollback removes explorer routes/navigation and returns to Phase 2 inspector. Immutable lineage/source objects stay for history/export.

## Done

- [x] Money trails preserve direction, order, Decimal, currency and coverage.
- [x] Ownership shows exact derivation and limitations.
- [x] Document comparison retains original-byte lineage and safe fallbacks.
- [x] Desktop/mobile/keyboard users can inspect every relationship.

## Execution evidence

Completed locally on 2026-10-11. See the [execution report](../reports/cook-261011-1326-investigator-workspace.md)
and [independent review](../reports/code-review-261011-workspace.md).
Provider behavior and deployed authentication remain Phase 6 live gates.
