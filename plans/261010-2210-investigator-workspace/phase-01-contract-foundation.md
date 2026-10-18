---
phase: 1
title: "Evidence and transaction-reason contracts"
status: pending
priority: P0
effort: "24-32 person-hours"
dependencies: []
---

# Phase 1: Evidence and transaction-reason contracts

## Goal

Create backwards-compatible typed contracts that identify what a transaction
reason is about, which records participate in a pattern, which records are only
context, and which ordering is actually known.

## Context and verified foundations

- The accepted ten-group scope and attribution boundary are in
  `plans/reports/brainstorm-261010-2204-investigator-workspace-features.md:198`.
- `Evidence.refs` is the only current source-membership field
  (`backend/casemind/models.py:135`), while the constructor sorts and deduplicates
  refs (`backend/casemind/analytics.py:9`). It cannot encode traversal order.
- Activity evidence identifies one target in `payload.transaction_id` but cites
  every baseline row (`backend/casemind/analytics.py:166`). Flow payloads contain
  ordered accounts and amounts but omit ordered transaction IDs
  (`backend/casemind/analytics.py:45`).
- Evidence is copied directly into report version one
  (`backend/casemind/investigation.py:323`); old payloads must remain readable.

## Requirements

- [ ] Preserve the current evidence/report JSON fields and accept existing report
      payloads that lack the new attribution fields.
- [ ] Represent `subject`, `pattern_participant`, and `context_baseline`
      independently; a source can have more than one explicit role only when the
      deterministic tool says so.
- [ ] Add ordered transaction IDs only at computation time. Legacy order that
      cannot be proven from its pinned snapshot is `unknown`, never reconstructed
      by assuming sorted refs are chronological.
- [ ] Derive exact amounts with `Decimal` and serialize decimal strings; never
      combine currencies without an explicit supported conversion.
- [ ] Express completed, not-evaluated, missing, failed, and truncated coverage.
      Per-family coverage distinguishes an insufficient baseline/skipped check from
      a completed negative test; global gaps/truncation remain separate. “No
      indicator found” stays bounded to completed checks and is not clearance.
- [ ] Keep observed facts, cautious interpretation, legitimate alternatives,
      limitations, and proposed next checks in separate fields.
- [ ] Add an explicit provenance taxonomy for public-real, public-synthetic and
      CaseMind-synthetic records while reading current `source_kind: synthetic`
      as a legacy synthetic value. This phase imports no public/real data.
- [ ] Do not expose evaluator ground truth or turn priority score into a transaction
      probability. Sanctions/PEP and transaction indicators do not establish crime.

## Data flow

1. A deterministic analytics function receives a validated `Case` snapshot.
2. It emits evidence with source membership plus typed attribution and, where the
   algorithm knows it, ordered transaction IDs.
3. A pure reason builder receives one transaction ID, the pinned case, evidence,
   run coverage, and tool versions. It validates all IDs against the snapshot.
4. The builder emits zero or more typed reasons plus one coverage assessment.
   Numeric facts come from evidence/source rows; prose templates cannot add facts.
5. Existing reports enter a compatibility adapter. Tool-specific fields may prove
   subject/context roles, but absent path order is returned as unavailable.

## Files to modify or create

| Action | Absolute path | Ownership and change |
|---|---|---|
| Modify | `/Users/thangluu/Repos/casemind-ai/backend/casemind/models.py` | Add optional attribution, coverage and transaction-reason models without breaking v1 payloads. |
| Modify | `/Users/thangluu/Repos/casemind-ai/backend/casemind/analytics.py` | Emit subject/participant/context roles and ordered IDs from live calculations. |
| Create | `/Users/thangluu/Repos/casemind-ai/backend/casemind/explanations.py` | Validate and build source-supported transaction explanations, including legacy handling. |
| Modify | `/Users/thangluu/Repos/casemind-ai/tests/test_contracts.py` | Cover schema round trips and old report compatibility. |
| Modify | `/Users/thangluu/Repos/casemind-ai/tests/test_analytics.py` | Cover attribution, order, Decimal facts, negative controls and truncation. |
| Create | `/Users/thangluu/Repos/casemind-ai/tests/test_explanations.py` | Exercise all reason families and legacy unknown-order behavior. |

No files are deleted. These files are phase-owned until its gate passes; phase 2
may then consume and extend the models serially.

## Implementation steps

1. Define strict enums/models for attribution role, coverage state, reason family,
   rule identity/version, deterministic fact values, evidence/source IDs,
   ordered path state, limitations, alternatives and next checks. Keep new
   `Evidence` fields optional with empty defaults so stored v1 evidence validates.
   Compatibility reads must not rewrite/re-serialize approved reports, change their
   hashes, or backfill stored artifacts. Version new tool output when semantics change.
   Add the compatible provenance value/adapter in the same schema boundary.
2. Update each analytics family:
   - `summarize_activity`: target is subject; other history rows are context.
   - `detect_structuring`: all cluster rows are pattern participants; sender is subject.
   - `trace_flows`/`detect_cycles`: emit ordered transaction IDs before `refs` sorting.
   - truncation/inventory observations: references are context, never indicators.
3. Implement the pure reason builder with explicit tool/version dispatch. Unknown
   tool versions return a labeled raw/unsupported explanation, not fabricated text.
4. For legacy flow evidence, validate membership but mark order unknown unless an
   unambiguous stored field proves it. Never infer order merely from refs, list
   position, amount, or timestamp ties.
5. Add schema and analytics tests that alter amount, currency, time and direction;
   ensure controls do not receive a reason and baseline rows do not inherit one.

## Verification gates

Run narrow, offline checks first:

```bash
./.venv/bin/python -m pytest tests/test_contracts.py tests/test_analytics.py tests/test_explanations.py -q
./.venv/bin/python -m ruff check backend/casemind/models.py backend/casemind/analytics.py backend/casemind/explanations.py tests/test_contracts.py tests/test_analytics.py tests/test_explanations.py
```

Then run the shared deterministic suite:

```bash
./.venv/bin/python -m pytest tests/test_store_api.py tests/test_reliability.py tests/test_investigation.py -q
```

Do not run `evaluation/run-evaluation.py` as an offline gate yet: its current
startup unconditionally reads cloud config and constructs `Cloud`
(`evaluation/run-evaluation.py:70`).

## Success criteria

- [ ] All four transaction reason families expose the correct role and exact facts.
- [ ] Sorted refs cannot masquerade as an ordered path; legacy uncertainty is visible.
- [ ] V1 report/evidence fixtures still parse and render a safe compatibility result.
- [ ] Failed, missing and truncated checks never return “no indicator found.”
- [ ] Every reason reference resolves inside the selected case/run snapshot.

## Risks and rollback

| Risk | Likelihood × impact | Mitigation |
|---|---|---|
| New fields change evidence IDs/hashes | High × High | Keep evidence ID inputs stable for existing tools or version the tool intentionally; fixture-test old hashes before merge. |
| Legacy adapter overstates order or role | Medium × High | Permit unknown states; dispatch only on verified tool/version fields. |
| Attribution changes priority semantics | Medium × Medium | Leave `follow_up_priority` contract unchanged in this phase and regression-test it. |

Rollback by stopping reads of the optional fields and reverting tool emission;
stored v2 payloads remain readable because the fields are additive. No data
migration or cloud action occurs in this phase.

## Todo

- [ ] Add additive typed contracts and compatibility fixtures.
- [ ] Emit deterministic attribution and ordered IDs.
- [ ] Build explanations and complete narrow/offline gates.
