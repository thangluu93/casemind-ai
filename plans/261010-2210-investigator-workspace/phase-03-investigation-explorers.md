---
phase: 3
title: "Money, ownership and document explorers"
status: pending
priority: P1
effort: "28-40 person-hours"
dependencies: [2]
---

# Phase 3: Money, ownership and document explorers

## Goal

Turn the shared source/reason foundation into coordinated, accessible money-trail,
ownership, and document comparison workspaces without inventing graph edges,
ownership certainty, or document-location precision.

## Context and verified foundations

- The transfer/ownership graph is currently a circular SVG over raw case records
  with an accessible link list (`frontend/src/flow-graph.tsx:4`).
- Flow analytics bound hops, time, ratios, results and work
  (`backend/casemind/analytics.py:45`). Ownership is per-path Decimal
  multiplication and explicitly not aggregation/legal UBO determination
  (`backend/casemind/analytics.py:210`).
- Document evidence contains confidence, page and text anchors, while cross-document
  mismatches currently lose per-value anchor lineage
  (`backend/casemind/analytics.py:366`).

## Requirements

- [ ] Money trail coordinates a directed graph and ordered transfer list with
      account, direction, time, currency, reason and path isolation controls.
- [ ] Display filters change presentation only. Any recomputation is an explicit
      bounded analysis action with persisted parameters and a new artifact.
- [ ] Exact per-edge decimal strings and currencies remain separate; truncation,
      tool bounds, unavailable order and missing records are visible.
- [ ] Ownership shows direct/indirect paths, step-by-step Decimal multiplication,
      declared-owner comparison, unknown percentages, cycles, overlap and depth
      limits. It never claims jurisdictional legal UBO status.
- [ ] Document comparison shows raw/normalized values, confidence, matched,
      conflicting, missing and low-confidence states. It uses page/text locators;
      it draws a region only when source data supplies a verified bounding box.
- [ ] Desktop and mobile layouts, keyboard navigation, focus return, loading,
      empty, partial and error states are complete for all three explorers.

## Data flow

1. A pinned/current source inventory feeds shared selection and explorer filters.
2. Money-trail display filters select source rows locally; reason/path overlays
   use typed phase-1 evidence and ordered IDs, never inferred order from refs.
3. Ownership cards consume `trace_ownership` path records and source relationships;
   each displayed multiplication links to every contributing relationship.
4. Document comparison joins extraction fields by document/field identity and
   retains each value's document, page, anchor, confidence and normalization.
5. Selecting any edge/path/value returns to the same phase-2 source inspector.

## Files to modify or create

| Action | Absolute path | Change |
|---|---|---|
| Modify | `/Users/thangluu/Repos/casemind-ai/backend/casemind/analytics.py` | Preserve per-document lineage for cross-document comparisons and any missing display metadata. |
| Modify | `/Users/thangluu/Repos/casemind-ai/frontend/src/api.ts` | Add exact explorer view types. |
| Modify | `/Users/thangluu/Repos/casemind-ai/frontend/src/main.tsx` | Compose explorer destinations with shared selection. |
| Modify | `/Users/thangluu/Repos/casemind-ai/frontend/src/case-navigation.tsx` | Add Money trail, Ownership and Documents destinations. |
| Modify | `/Users/thangluu/Repos/casemind-ai/frontend/src/flow-graph.tsx` | Accept controlled filters/selection and remove `Number` money formatting. |
| Create | `/Users/thangluu/Repos/casemind-ai/frontend/src/money-trail.tsx` | Ordered list, filters, path controls and reason integration. |
| Create | `/Users/thangluu/Repos/casemind-ai/frontend/src/ownership-explorer.tsx` | Path table, derivation and limitations. |
| Create | `/Users/thangluu/Repos/casemind-ai/frontend/src/document-comparison.tsx` | Comparable fields and PDF/page/text context. |
| Modify | `/Users/thangluu/Repos/casemind-ai/frontend/src/styles.css` | Responsive graph/table/document layout and print-safe source panels. |
| Modify | `/Users/thangluu/Repos/casemind-ai/tests/test_analytics.py` | Document lineage, ownership overlap/null/cycle, and path bounds. |
| Create | `/Users/thangluu/Repos/casemind-ai/tests/test_explorer_contracts.py` | Serializations and invalid/missing source behavior. |

No new server/service or graph database is introduced. Existing bounded demo
collections use local display filters.

## Implementation steps

1. Extend document mismatch payloads so each compared value retains document ID,
   raw value, normalized value, page, anchors and confidence. Keep old evidence
   compatible and show missing lineage explicitly.
2. Refactor `FlowGraph` into a controlled, accessible source view. Preserve SVG
   direction and the complete accessible list; compute labels from exact strings.
3. Build Money trail using ordered IDs supplied by phase 1. Show unavailable
   ordering for legacy artifacts, all tool caps, and hidden-row counts.
4. Build Ownership explorer directly from relationship/path evidence. Detect and
   label overlapping paths; never sum them unless a future deterministic contract
   explicitly handles deduplication.
5. Build Document comparison with responsive PDF/source panels. Use verified page
   navigation and text excerpts; never translate offsets into guessed rectangles.
6. Connect all selections to the shared inspector/reason panel and test broken,
   missing, partial, low-confidence and truncated cases.

## Verification gates

```bash
./.venv/bin/python -m pytest tests/test_analytics.py tests/test_explanations.py tests/test_explorer_contracts.py -q
./.venv/bin/python -m ruff check backend/casemind/analytics.py tests/test_analytics.py tests/test_explorer_contracts.py
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

Manual offline acceptance uses seeded fixtures and must cover 375, 768 and 1440
pixel widths plus keyboard-only source traversal. Do not invoke live e2e here.

## Success criteria

- [ ] Transfer direction/order and exact values match source rows for all flow cases.
- [ ] Ownership calculations preserve unknowns and disclose cycles/overlap/depth.
- [ ] Every document value resolves to its evidence and best available locator.
- [ ] No guessed graph edge, aggregate percentage, bounding box or accusation appears.
- [ ] Every visible link is operable by keyboard and has an accessible source list.

## Risks and rollback

| Risk | Likelihood × impact | Mitigation |
|---|---|---|
| Dense graphs become unusable | Medium × Medium | Bounded path isolation, ordered list and source-first fallback. |
| Ownership paths are double-counted | Medium × High | Per-path display only and explicit overlap labels. |
| Text anchors imply visual precision | High × High | Page/text fallback unless verified region data exists. |

Rollback each explorer destination independently to phase-2 source/card views.
The additive document lineage remains useful and does not alter old report hashes.

## Todo

- [ ] Preserve document comparison lineage.
- [ ] Deliver money, ownership and document explorers.
- [ ] Pass deterministic, build, responsive and keyboard gates.
