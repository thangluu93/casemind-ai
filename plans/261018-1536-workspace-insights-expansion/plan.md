---
title: Workspace insights expansion (groups A and B)
date: 2026-10-18
timezone: Asia/Ho_Chi_Minh
status: implemented_locally
source: user request "nhóm A + B" after the 2026-10-18 brainstorm
---

# Workspace insights expansion

## Contract

- **Outcome:** twelve additions to the investigator workspace. Group A:
  in-app evaluation scorecard, guided demo, and a prompt-injection safety
  control case. Group B: devil's-advocate challenge, ranked "what would change
  the conclusion", RFI drafts, typology mapping, threshold what-if, bounded
  graph query with model-planned queries, temporal replay, maker-checker
  review, triage queue and a Vietnamese/English report export.
- **Constraints:** existing reports, review records and their hashes stay
  byte-compatible; every new view derives from the pinned snapshot and recorded
  evidence. Numbers come from deterministic tools; model prose stays digit-free
  and cites only pinned evidence IDs. Model calls reuse the bounded operation
  authority (idempotency key, quota, fenced deadline). The five requested
  scenarios are unchanged; the injection case is an added safety control.
  Ground truth never enters the runtime, including the evaluation summary.
- **Non-goals:** cloud deployment, spending, OAuth configuration, sending any
  RFI, automatic disposition, real typology certification, and machine
  translation of model prose.
- **Acceptance:** backend tests cover each deterministic builder and route;
  default analytics outputs and evidence IDs are unchanged; the injection case
  is detected and redacted before model context; ruff, pytest, frontend
  typecheck and build pass. Live Gemini paths remain unverified until a
  separately authorized live run.

## Design

| Feature | Backend | Frontend |
|---|---|---|
| Evaluation scorecard | `scripts/build-evaluation-summary.py` writes aggregate-only `casemind/data/evaluation-summary.json`; `GET /api/evaluation` | Evaluation tab |
| Guided demo | none | Header button with step overlay; never auto-runs billed work |
| Injection control | `generator.injection_control_case`; `analytics.detect_embedded_instructions`; redaction in model-facing tool payloads | Labeled sixth case |
| Typologies | `insights.typology_map` | Typologies tab |
| What-if | parameterized analytics with unchanged defaults; `insights.simulate_thresholds` | What-if tab |
| Change drivers | `insights.change_drivers` ranked by triage weight | Challenge tab |
| Alternative checks | `insights.alternative_checks` | Challenge tab |
| Challenge and RFI | `advisory.py` bounded cited synthesis via `Operations` | Challenge and RFI tabs |
| Graph query | `insights.run_graph_query`; model-planned `GraphQuery` shown before execution | Graph query tab |
| Replay | none (pinned transactions) | Replay tab |
| Maker-checker | `checks/` request and immutable checker decision, distinct authenticated actor | Review panel |
| Triage queue | `GET /api/triage` from owned history | Triage tab |
| Bilingual export | `exports.render_html(view, lang)`; `?lang=vi` | Export link |

## Phases

1. Group A backend and UI.
2. Deterministic insights (typologies, what-if, change drivers, alternative
   checks, graph query) with tests.
3. Advisory model paths (challenge, RFI, graph-query planning) with offline
   validation tests.
4. Workflow additions (replay, maker-checker, triage, bilingual export).
5. Verification, docs update, report.
