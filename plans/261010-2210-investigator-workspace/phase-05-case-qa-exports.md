---
phase: 5
title: "Scoped case Q&A and offline HTML/PDF/JSON exports"
status: pending
priority: P2
effort: "36-48 person-hours"
dependencies: [2, 4]
---

# Phase 5: Scoped case Q&A and offline HTML/PDF/JSON exports

## Goal

Add bounded, cited case Q&A and three equivalent owner-scoped export formats:
existing JSON plus safely escaped printable HTML and generated PDF that remain
useful offline without public share links.

## Context and verified foundations

- Model synthesis validates citation membership and rejects digits in prose
  (`backend/casemind/investigation.py:87`), but semantic support still needs review.
- The model/tool call budget is per investigation (`backend/casemind/investigation.py:39`);
  phase 4 must extend the global reservation boundary before Q&A is enabled.
- The current report endpoint returns JSON (`backend/casemind/main.py:303`) and the
  UI exposes only that download (`frontend/src/investigation-report.tsx:34`).
- `reportlab` is already pinned (`pyproject.toml:13`).

## Requirements

- [ ] Q&A is bound to one owned run/snapshot/report. Retrieval can access only its
      case, evidence, report, reviews, assessments and follow-up artifacts.
- [ ] Supported questions explain a finding, show supporting/conflicting evidence,
      summarize gaps, compare supplied records and discuss legitimate alternatives.
      “Why was this transaction flagged?” delegates to deterministic reasons.
- [ ] Quantitative answers use deterministic facts/templates. Model prose remains
      interpretive, digit-free under the existing boundary, cited and abstaining
      when evidence is missing or contradictory.
- [ ] Questions/document text are untrusted data. No arbitrary SQL, URL fetch,
      cross-case retrieval, new implicit run, write action or disposition is allowed.
- [ ] Every request is idempotent, globally reserved, owner-scoped, capped by model
      calls/tokens, and completed in the same request under a hard deadline.
- [ ] Q&A records are immutable and expose failure, reservation, scope, citations
      and abstention. Factual claims receive semantic-support review in evaluation.
- [ ] JSON behavior stays compatible. Printable HTML and PDF use one canonical
      export view model and include matching findings, reasons, alternatives,
      limitations, coverage, source excerpts/locators, synthetic/provenance labels,
      report hash/version and human review assurance.
- [ ] Keep `GET /api/runs/{run_id}/report` response and report hash semantics
      unchanged. A new canonical export JSON route is additive and cannot rewrite,
      reserialize or replace the immutable stored report artifact.
- [ ] Exports escape all untrusted content and make offline access limitations
      explicit. They contain no active session secret, ground truth or public URL.

## Data flow

1. UI sends question, run ID and idempotency key to an owned-run endpoint.
2. Server classifies the allowed question family and builds a bounded retrieval set
   from the pinned report/snapshot. Transaction-reason questions return deterministic
   output directly; other families reserve and call the bounded Q&A synthesizer.
3. Validator checks answer shape, scope, citation membership, numeric boundary and
   abstention. The immutable Q&A artifact stores request, retrieval IDs, response,
   usage/failure and report hash.
4. Export builder loads owned immutable artifacts into a canonical view model,
   including permitted source excerpts and explicit missing-access notes.
5. Additive export JSON, escaped HTML and ReportLab PDF render from the same view
   model. The existing `/report` endpoint continues returning its stored artifact
   unchanged. Downloads use safe filenames and `Content-Disposition`; no public
   sharing is created.

## Files to modify or create

| Action | Absolute path | Change |
|---|---|---|
| Modify | `/Users/thangluu/Repos/casemind-ai/backend/casemind/models.py` | Q&A request/answer and canonical export models. |
| Modify | `/Users/thangluu/Repos/casemind-ai/backend/casemind/investigation.py` | Extract reusable bounded model runner/validation without widening specialist tools. |
| Create | `/Users/thangluu/Repos/casemind-ai/backend/casemind/case_qa.py` | Allowed-family retrieval, deterministic routing, synthesis and validation. |
| Create | `/Users/thangluu/Repos/casemind-ai/backend/casemind/exports.py` | Canonical view model plus JSON/escaped HTML/ReportLab PDF renderers. |
| Modify | `/Users/thangluu/Repos/casemind-ai/backend/casemind/main.py` | Add owned Q&A and format-specific export routes. |
| Modify | `/Users/thangluu/Repos/casemind-ai/frontend/src/api.ts` | Q&A and export contracts. |
| Modify | `/Users/thangluu/Repos/casemind-ai/frontend/src/main.tsx` | Compose Q&A and export controls. |
| Create | `/Users/thangluu/Repos/casemind-ai/frontend/src/case-qa.tsx` | Cited conversation, abstention, quota and failure states. |
| Modify | `/Users/thangluu/Repos/casemind-ai/frontend/src/investigation-report.tsx` | Add JSON/HTML/PDF choices and export scope explanation. |
| Modify | `/Users/thangluu/Repos/casemind-ai/frontend/src/styles.css` | Q&A and printable report rules. |
| Create | `/Users/thangluu/Repos/casemind-ai/tests/test_case_qa.py` | Scope, abstention, adversarial input, citations, bounds and idempotency. |
| Create | `/Users/thangluu/Repos/casemind-ai/tests/test_exports.py` | Format parity, escaping, exact values and immutable-version binding. |
| Modify | `/Users/thangluu/Repos/casemind-ai/tests/test_investigation.py` | Reusable runner and model-call-bound regression. |

Use Python module name `case_qa.py` to follow language conventions. Proposed routes
are `POST /api/runs/{run_id}/questions` and
`GET /api/runs/{run_id}/exports/{json|html|pdf}`; they do not exist today.

## Implementation steps

1. Define strict question families and retrieval caps by evidence/source count and
   serialized bytes. Treat unsupported requests as abstentions rather than tool access.
2. Route transaction-reason and exact-value questions to deterministic builders.
   For interpretive families, reuse safety/call bounds but provide only the selected
   evidence subset and no mutating/arbitrary tools.
3. Reserve Q&A globally before provider work, apply operation idempotency and lease,
   execute in the request, persist immutable success/failure and retain reservations.
4. Validate citation membership and answer scope mechanically; add a separate
   evaluation field for human semantic support rather than claiming citations prove it.
5. Build a canonical export model from the exact report/review/snapshot versions.
   Include safe excerpts/locators where permitted and explicit unavailable-source text.
6. Render escaped semantic HTML with print CSS and a PDF from the same ordered
   sections. Preserve decimal strings and currencies; never pass untrusted text as
   HTML markup or PDF formatting directives.
7. Add UI question history, citation navigation, visible costs/failures and explicit
   export format controls. Keep JSON as an unchanged option.

## Verification gates

```bash
./.venv/bin/python -m pytest tests/test_case_qa.py tests/test_exports.py tests/test_investigation.py tests/test_store_api.py -q
./.venv/bin/python -m ruff check backend/casemind/case_qa.py backend/casemind/exports.py backend/casemind/investigation.py backend/casemind/main.py tests/test_case_qa.py tests/test_exports.py
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

Provider-bound Q&A evaluation is a later explicitly authorized billed gate. Unit
tests use boundary fixtures and do not claim semantic quality.

## Success criteria

- [ ] Cross-case/adversarial questions cannot widen retrieval or tools.
- [ ] Unknown/contradictory questions abstain; exact-value answers match sources.
- [ ] Duplicate Q&A requests produce one reservation and immutable artifact.
- [ ] HTML safely escapes scripts/markup; PDF and HTML contain the same canonical
      sections, exact amounts, source IDs, labels, limitations, hash and review.
- [ ] Downloads work offline and explain unavailable original-source access.

## Risks and rollback

| Risk | Likelihood × impact | Mitigation |
|---|---|---|
| Persuasive answer lacks semantic support | High × High | Bounded retrieval, abstention, citation validation and human semantic evaluation. |
| Export injection or data leak | Medium × High | Canonical allowlisted fields, context-aware escaping, owner checks and no session URLs/secrets. |
| HTML/PDF drift | Medium × Medium | One view model and parity fixtures for headings/facts/metadata. |

Rollback disables Q&A and new format routes independently. Existing JSON remains
available; immutable Q&A artifacts and generated exports are retained for audit.

## Todo

- [ ] Implement bounded retrieval, deterministic routing and immutable Q&A.
- [ ] Implement canonical JSON/HTML/PDF export rendering and escaping.
- [ ] Deliver UI and pass scope, parity, build and security gates.
