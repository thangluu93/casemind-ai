---
title: Complete investigator workspace implementation
date: 2026-10-11
summary: Ten feature groups implemented locally; offline verification passes and live release gates remain pending.
---

# Complete investigator workspace implementation

Implemented the accepted six-phase workspace plan using the ak-cook workflow. Added visible Watchlist navigation, scoped sources/findings/reasons, deterministic explorers, original-PDF lineage, restricted synthetic intake, child snapshots, recoverable fenced operations, history, cited Q&A and HTML/PDF alongside existing JSON.

Independent review found execution fencing, full OCR export exposure, login throttling, uncited numeric answers, order-dependent intake and incomplete recovery pagination. These were repaired with focused regressions. Real 50-page PDF tests exposed a stale 20-page cap; parser/ledger now accept the planned limit and Document AI uses selected-page batches against unchanged originals. A concurrent quota test incorrectly assumed request zero won the race; it now verifies replay of actual successful reservations.

Final local gates: 87 Python tests, Ruff, frontend typecheck/build and 19 offline browser tests passed. Fifty generated evaluation cases yielded 45 TP, zero FP/FN and zero errors in the template metric; OCR/model quality remains unmeasured. No cloud spending/configuration/deployment/publication or persistent-state migration occurred. Live GIS configuration and provider/deployed browser acceptance remain required before release readiness.

> Historical work record — not durable authority. Prefer docs/specs/ADRs for current decisions.
