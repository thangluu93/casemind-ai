# Scenarios and evaluation

Proposed benchmark and targets, 2026-10-09. Initial live measurements and unmet
gates are recorded in [delivery evidence](../plans/reports/261009-prototype-delivery.md). Synthetic ground truth describes constructed behaviors, not
legal conclusions or real-world model generalization.

## Five required scenarios

| Scenario | Inputs and expected findings | Ground truth and evidence | Indicators and evaluation |
|---|---|---|---|
| Layering | Transfers among fictional entities over a bounded window, ordinary supplier payments and some ownership/KYC context. Find time-respecting multi-hop paths and rapid pass-through activity; consider legitimate settlement. | Ordered transaction IDs, times, amounts and planted pattern IDs in evaluator-only truth. Cite each selected edge and computed timing/amount feature. | Layering indicators, flow-path precision/recall, amount/time exactness, counterexample rejection. No assertion of criminal origin. |
| Hidden beneficial ownership | Fictional corporate register, shareholder declarations, indirect and direct interests, plus incomplete/cyclic controls. Trace supported natural-person interests and flag declaration discrepancies. | Known percentages/paths and expected unknown cases. Cite relationship records and declaration page/field anchors. | Ownership-path and percentage correctness, missing-link abstention, false identity merge rate. Demo policy is explicit and configurable. |
| Sanctions/PEP false positive | Synthetic sanctions and PEP entries, a similar-name person with conflicting identifiers, a true-match control and an incomplete-identity control. Return explained candidate assessments. | Expected `false_positive`, `potential_match`, or `inconclusive` dispositions and attribute-level truth. Cite subject and watchlist attributes. | Candidate recall, false-positive rate, correct disambiguation and abstention. PEP status alone must not imply sanctions or criminality. |
| Inconsistent KYC documents | Watermarked fictional KYC form and KYB/identity declarations with name/ID/ownership differences, benign formatting changes and low-quality fields. Extract and compare normalized values. | Expected field values, document types, page anchors and mismatch IDs. Preserve original fields and normalization operations. | Extraction exact match by field, mismatch precision/recall, citation/page accuracy. Unsupported or low-confidence extraction stays unresolved. |
| Circular transactions | Directed transfers A→B→C→A plus an undirected triangle, wrong-time-order cycle and legitimate refund controls. Detect only qualifying directed temporal cycles. | Ordered edge IDs, cycle windows and configured retained-value tolerance. Cite original rows and time/amount calculations. | Cycle precision/recall, false detection on controls, currency handling, bounded enumeration and reported truncation. Circularity is an indicator. |

Structuring, anomaly detection and suspicious networks are additional indicators
within the transaction scenarios, not replacement scenarios. Include a normal
cash-intensive pattern, near-threshold splitting pattern, sparse-history case
and a connected-but-unrelated network control. Proposed configurable demo
structuring rule: at least three same-currency transfers under a threshold `T`
from a sender in 24 hours with total above `T`. `T` is test configuration, not a
statement of regulatory requirements. Label the rule in findings.

## Benchmark construction and separation

Start with 50 generated cases: for each scenario, five positive variants and
five controls (benign, ambiguous, missing-data or contradictory). Split by seed,
identity and topology family into 20 development and 30 held-out cases, balanced
as far as possible. Parameter variation alone is not an independent topology.
Keep five representative demo cases separate from held-out scoring.

Freeze generator, inputs, labels and evaluation configuration with hashes before
running the held-out set. Labels never enter model prompts, retrieval or tools.
Run the held-out set three times with pinned model/prompts and report variation.
IBM AML-Data forms a separate external transaction evaluation: acquire a bounded
labeled subset, split connected entities/time periods to reduce leakage, and
report row/flow metrics separately. Do not use its binary transaction labels as
ownership, sanctions or document ground truth.

## Metrics and proposed release gates

| Layer | Measurement | Proposed gate |
|---|---|---|
| Deterministic analytics | Known path/cycle/ownership/amount fixtures and negative controls | Exact expected numeric/path results on bounded fixtures; no silent truncation or cross-currency summation |
| Citation integrity | Resolved cited IDs / all cited IDs; correct case/run scope | 100% resolution and scope correctness; wrong-case evidence blocks report completion |
| Evidence support | Supported factual claims / factual claims, independently reviewed | At least 95% on held-out reports, zero unsupported identity links or accusations |
| Scenario detection | Precision/recall by scenario and finding type, with raw TP/FP/FN | Target at least 90% each for constructed indicators; publish counts and failures rather than claim general accuracy |
| Screening restraint | Correct false-positive/inconclusive dispositions, separately from candidate recall | All designated similar-name and missing-identity safety controls pass |
| Document comparison | Raw extraction accuracy and normalized mismatch accuracy by field | All demo required fields have correct values or explicit unresolved status; target 90% held-out mismatch precision/recall |
| Human review | Version-bound approve/reject/follow-up and persistence after restart | Every action records a reason and survives service restart; conflicting updates are rejected visibly |
| Runtime | Warm/cold latency, completion rate, calls, tokens, pages, bytes billed, cost | Target warm p95 under 90 seconds on demo-sized inputs; termination by 120 seconds; enforce the proposed quotas and spend allocation in research findings |

Small sample results require raw counts and uncertainty, not just percentages.
Do not tune held-out rules to reach the targets. Targets are proposed engineering
gates, not measured claims or guaranteed feasibility.

## Verification methods

Compare a deterministic-tools-only baseline with the agent workflow on the same
inputs. Measure whether synthesis improves explanation completeness and handling
of competing evidence; do not attribute deterministic detection to Gemini.
Review citations and source facts using evaluator-only truth plus human spot
checks. A model judge can help assess readability, but cannot determine ground
truth correctness alone.

Test altered amounts, reversed edges, reordered timestamps, duplicate names,
missing DOB/ID, unknown ownership percentages, mixed currencies, inaccessible
sources, malformed extraction, provider timeout/quota errors, browser reconnect,
concurrent review and service restart. Add document prompt-injection controls
that request scope expansion or evidence fabrication; tools must deny them.

Change one input and rerun: affected facts must change while unaffected facts
remain stable. This is the central proof that the demo executes analysis rather
than displaying prewritten findings. Record tools, arguments, outputs and hashes.

An incomplete run yields `completed_with_gaps` or a visible failure, never a
silently complete report. No unsupported claim survives validation. Retry
provider errors within the deadline; do not replace live Gemini output with a
canned report and call the run successful.

## Demonstrating impact

Time a small investigator task with and without the workspace, recording task
definition, evidence checked, participants and errors. Treat the result as a
pilot observation, not a bank-wide productivity promise. Until measured,
describe intended value: fewer manual joins and easier verification.

## Workspace offline gate

Run `PYTHONPATH=backend ./.venv/bin/python evaluation/run-evaluation.py --split all
--repeats 1 --concurrency 1` without `--live`. This path uses a labelled synthetic
field adapter and never constructs Cloud or reads cloud configuration/credentials.
It records mode, source/configuration hashes and time, and explicitly marks OCR
quality unmeasured. `--live` remains an explicit billed-provider gate.

The workspace browser gate is `npm --prefix frontend run test:e2e:offline`, using
a temporary real-route test server on port 8081. Seed routes/fixtures are test-only
and excluded from the runtime container. Test artifacts live under the accepted
workspace plan reports directory. Use `test:e2e:live` only against a separately
authorized deployment with `CASEMIND_TEST_URL`.

See the [execution report](../plans/reports/cook-261011-1326-investigator-workspace.md)
for actual counts. Offline template detection, source scope and citation membership
do not establish OCR accuracy, semantic Q&A support or live release readiness.
