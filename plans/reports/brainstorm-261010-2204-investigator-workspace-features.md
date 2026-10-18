---
title: CaseMind investigator workspace feature brainstorm
date: 2026-10-10
timezone: Asia/Ho_Chi_Minh
status: proposed
type: brainstorm-report
scope: ten feature groups
---

# CaseMind investigator workspace feature brainstorm

## Summary

Evolve the existing prototype into an investigation workspace where an analyst
can inspect inputs, understand why a transaction was flagged, test explanations,
and record a source-backed human decision. The current backend already computes
several useful findings; much of the user experience still presents them as JSON
or generic evidence entries.

This report covers all nine previously discussed feature groups and the user's
additional request to explain why a transaction is considered suspicious. It
authorizes no implementation, deployment, cloud spending, or external data use.
Priorities describe delivery order, not removal of requested scope.

The recommended direction is an evidence-first workspace: make Watchlist,
Sources, Findings, and transaction explanations visible first, then connect
money trails, ownership and documents, followed by actionable follow-up, bounded
case Q&A, and history with readable exports.

## Brainstorm contract

- **Outcome:** a complete feature proposal for a richer CaseMind investigation
  experience, including transaction-level explanations and traceable decisions.
- **Constraints:** retain Google Cloud AI, one deployable service, five distinct
  investigation scenarios, deterministic calculations, scoped source evidence,
  synthetic labels, and human review. Preserve existing immutable reports and
  reviews. Retain the documented gross service budget below 1,000,000 VND and
  October 17 freeze as planning constraints; this report does not verify current
  expenditure or promise completion of every feature before the freeze.
- **Non-goals:** production bank integration, automatic blocking or filing,
  jurisdictional certification, unrestricted uploads or URL ingestion, real
  watchlist acquisition, enterprise multi-user workflow, or automatic findings
  of criminality. No code changes are included in this delivery.
- **Acceptance criteria for this report:** cover all ten groups; distinguish
  implemented foundations from proposals; specify user flows, data needs,
  dependencies, limitations, and observable acceptance for each; compare viable
  directions; recommend sequencing; end with unresolved product decisions.
- **Trade-offs:** screening-first produces a focused matching demonstration but
  leaves transaction investigation shallow; evidence-first uses existing tools
  across all scenarios but needs coordinated UI state and source links;
  chat-first offers flexible questions but depends on retrieval, citation
  validation, and bounded execution before its answers can be trusted.
- **Better approach:** expose structured evidence and source navigation before
  making chat the primary interface. Existing analytics and source APIs support
  the former; the current frontend has no Q&A workflow. The operational delta is
  richer inspection without a model call for every interaction. Switching costs
  are new workspace views and typed presentation contracts; no new service is
  needed for the initial foundation.

## Evidence and current-state boundary

Inspection covers local source on October 10. No new live model run or browser
verification was performed for this report. The earlier design report records
deployment verification; it is historical evidence, not a fresh live check.

| Area | Confirmed local behavior | Gap addressed by this proposal |
|---|---|---|
| Navigation | Sidebar lists synthetic cases; header counts transfers, entities and documents | No dedicated Watchlist or Sources navigation |
| Screening | Case API includes watchlist records; deterministic screening compares names and shared identifiers | Results and original records appear through generic evidence/JSON inspection |
| Sources | Case- and run-scoped record/PDF routes exist | No searchable source inventory before investigation |
| Findings | Evidence ledger, hypotheses, alternatives, unresolved questions and priority contributors exist | No readable typed cards or transaction reason panel |
| Graph | Directed transfer/ownership views, source selection and cited-record highlighting exist | No account/time filters, ordered trail view, or ownership derivation explorer |
| Documents | Extraction/comparison evidence contains fields, confidence and page/text anchors | PDFs open separately; no side-by-side field comparison |
| Review | One immutable decision with reason is bound to a report hash/version | Follow-up is a disposition, not an executable task workflow |
| History/export | Latest run key is retained in browser local storage; report JSON can be downloaded | No browsable server-side run history, diff, or readable report export |
| Q&A | Specialist investigation and synthesis exist | No user question endpoint or chat UI |

Source references:

- [Workspace composition](../../frontend/src/main.tsx)
- [Navigation and counts](../../frontend/src/case-navigation.tsx)
- [Frontend API types](../../frontend/src/api.ts)
- [Evidence and human review](../../frontend/src/evidence-review.tsx)
- [Report and timeline](../../frontend/src/investigation-report.tsx)
- [Directed source graph](../../frontend/src/flow-graph.tsx)
- [Deterministic analytics](../../backend/casemind/analytics.py)
- [Record schemas](../../backend/casemind/models.py)
- [Synthetic generator](../../backend/casemind/generator.py)
- [API and session checks](../../backend/casemind/main.py)
- [Persistence and usage reservations](../../backend/casemind/store.py)
- [Demo priority policy](../../backend/casemind/priority.py)
- [Analytics controls](../../tests/test_analytics.py)

The architecture and data-model documents describe intended contracts and still
contain proposal-era statements. Read them as design authority, while using code
and recorded verification for claims about implementation. For example, current
records use `source_kind: synthetic`; the broader three-category provenance
taxonomy is a design target, not a claim about current runtime enums.

## Proposed information architecture

Keep case selection visible and give the selected case these destinations:

| Destination | Contents |
|---|---|
| Overview | Input coverage, run state, findings, gaps and next steps |
| Sources | Transactions, entities, accounts, relationships, documents and watchlist |
| Watchlist & Screening | Supplied list, candidates, identity comparison and review |
| Money trail | Directed graph, ordered transfers, filters and transaction reasons |
| Ownership | Supported interests, path calculations and declaration differences |
| Documents | Original pages, extracted fields and comparisons |
| Investigation | Execution timeline, hypotheses, follow-up and case Q&A |
| Report & History | Version-bound assessment, review, run comparison and exports |

Use one source inspector and one evidence-selection mechanism across views.
Watchlist navigation is a discoverable shortcut into the same source records,
not a second database. Every destination must state whether it shows the current
case inputs or an immutable run snapshot. A pending or failed run must not leave
old findings looking like results from the new run.

## 1. Watchlist & Screening — P0

**User value:** see what list was actually checked and understand why a candidate
is a possible match, a likely false positive, or unresolved.

**Flow:** open Watchlist → search/filter supplied records → choose a candidate
or subject → compare identity fields → inspect both original records → record a
human assessment with reason.

**Proposed behavior:**

- Separate tabs or filters for Sanctions and PEP; show source and synthetic label.
- Display record name, category, available identifiers and source ID.
- Show a candidate table with subject, list record, name similarity and tool status.
- Compare each identifier as matched, conflicting, missing or not comparable.
- Label similarity as a name comparison, never a probability of identity or crime.
- Show missing attributes explicitly; do not turn a missing DOB into agreement.
- Keep tool assessment separate from human candidate assessment.

**Existing foundation:** `screening_analysis` and run-scoped sources. The current
generator supplies watchlist entries only for the screening scenario.

**Required extension:** typed screening presentation; candidate-scoped review
records if separate candidate decisions are implemented. Alias, provider refresh,
listing dates and status need actual source/schema support; omit unavailable
fields rather than invent them. No external watchlist provider is included.

**Acceptance:** both categories remain distinct; conflicting and incomplete
identity controls stay visible; each compared value opens its source; an empty
list says no list was supplied rather than implying screening clearance; saving
a candidate review cannot mutate the existing report review.

## 2. Source explorer — P0

**User value:** inspect the evidence inventory before relying on an AI report.

**Flow:** open Sources → choose record type → search/sort/filter → select a row
→ read structured details or original JSON/PDF → navigate to related records.

**Proposed behavior:** tables for transactions, entities, accounts, relationships,
documents and watchlist; stable record IDs; coverage counts; exact amounts and
currencies; original and localized timestamps; explicit missing values; links
to supplied related records. Raw JSON remains available as a secondary view.

**Existing foundation:** case collections and record/PDF lookup routes.

**Required extension:** typed table models and consistent selection state. Use
local filtering for bounded demo collections; add server pagination only when
actual dataset size requires it. Resolve case/run scope on the server for links.

**Acceptance:** accessible before a run; counts match the loaded snapshot; no
ground truth is visible; filters disclose hidden rows; unavailable records show
an explicit error; run evidence opens its pinned source rather than latest input.

## 3. Finding cards — P0

**User value:** understand a finding without reading a tool payload.

**Flow:** open Findings → filter by domain/type/status → select a card → see
supporting evidence, relevant graph records and source details.

**Proposed behavior:** each card includes a plain-language title, observation,
indicator or hypothesis label, verification status, deterministic facts, source
references, limitations, legitimate alternatives and useful next checks. Group
overlapping findings for display while retaining all underlying evidence IDs.

**Existing foundation:** `Evidence`, report synthesis, source links and priority
contributors. Evidence and model hypotheses are different objects today.

**Required extension:** tool-specific renderers and a typed view model. Render
numbers from tool payloads; keep model interpretation separate. Unknown tool
versions retain a labeled raw view instead of crashing or inventing a summary.

**Acceptance:** every displayed factual claim maps to evidence; hypothesis text
is visibly interpretive; priority contributors are inspectable; grouping does
not discard citations; gaps and unsupported fields remain visible.

## 4. Why this transaction was flagged — P0

**User value:** answer the user's explicit question: why does this particular
transaction need investigation, and what evidence supports that explanation?

**Flow:** select a transfer in Sources, a graph edge or a finding → open the
transaction reason panel → inspect the triggering rule and surrounding transfers
→ consider alternatives and missing information → open a follow-up or review.

**Proposed panel:**

1. **Assessment:** indicator participant, contextual record, not evaluated, or
   no indicator found within the completed checks. State run and coverage.
2. **Observed behavior:** concise description of the computed pattern.
3. **Rule and actual values:** tool/version, parameters, time window, currency,
   amounts/counts and the values that satisfied the rule.
4. **Role in the pattern:** flagged subject, member of a transfer cluster/path,
   or baseline/context only; show direction and chronological order.
5. **Supporting sources:** selected transaction and other relevant records.
6. **Interpretation and alternatives:** why the pattern merits checking, plus
   plausible settlement, refund or business explanations where applicable.
7. **Limitations and next checks:** missing history, incomplete search, unknown
   purpose, missing invoice or other evidence that could change the assessment.

**Initial reason families supported by current tools:**

| Reason family | Facts to expose | Required restraint |
|---|---|---|
| Multi-hop transfer pattern | Ordered accounts/transfers, elapsed time, per-edge amounts, retained ratio and configured bounds | A connected path does not establish that the same funds or unlawful proceeds moved through it |
| Circular transfers | Directed time-respecting return path, duration and retained ratio | A refund or settlement can be legitimate; an undirected triangle is insufficient |
| Structuring-like pattern | Same sender/currency, transfer count, window, total and demo threshold | The current 5,000 threshold is demonstration configuration, not a regulatory requirement or proof of evasion |
| Amount relative to supplied history | Target transaction, supplied baseline rows, median, multiple and sample size | A small synthetic sample is insufficient for population-wide anomaly claims |

**Existing foundation:** `trace_flows`, `detect_cycles`, `detect_structuring`,
`summarize_activity`, evidence references and derivation parameters.

**Critical attribution boundary:** reference membership alone cannot determine
whether a transaction was flagged. Activity evidence references baseline rows
as well as its target `transaction_id`; inventory and truncation evidence can
reference many rows without flagging any. Path/cluster evidence needs a pattern
participant role. Preserve these distinctions in a server-derived explanation.

**Required extension:** a typed explanation contract containing transaction ID,
run/snapshot identity, evidence IDs, reason code, participant role, deterministic
facts, rule/version, coverage and limitations. Preserve ordered transaction IDs
explicitly for path explanations: existing evidence references are sorted and
deduplicated, so their order must not be treated as traversal order. Resolve all
numeric values using tools/source records, with exact decimal formatting.

**Presentation example, not an executed result:** “This transfer is part of a
same-currency cluster that meets the configured demonstration count, amount
and time-window rule. Inspect the cluster and payment purpose before making a
decision.” The real panel fills values from that run's evidence.

**Acceptance:**

- Every reason resolves to a supported indicator and the correct participant role.
- Baseline/context rows never inherit the target transaction's anomaly flag.
- Changing amount, currency, timing or direction changes the applicable reason
  according to deterministic analysis; legitimate controls remain unflagged.
- No indicator found is not clearance; failed/missing/truncated checks show gaps.
- Case priority is never reused as a transaction probability or unexplained score.
- Clicking a rule opens its actual parameters and original rows; optional model
  prose cannot introduce numeric facts or unsupported reasons.
- Interpretations and alternatives remain distinct from observed facts and do
  not accuse the customer of criminality.

## 5. Interactive money trail — P1

**User value:** move from an interesting transaction to its supported surrounding
flow without manually joining rows.

**Flow:** choose account/transaction → select direction, time range and currency
→ inspect a bounded path → select an edge → read its reason and original record.

**Proposed behavior:** coordinated graph and ordered transfer list; account and
time filters; path isolation; chronological stepping; per-edge values; explicit
cycle/structuring overlays; displayed tool bounds and truncation indicators.

**Existing foundation:** directed graph, highlighting and deterministic paths.

**Required extension:** ordered path IDs and graph view state. Visual filters
must be labeled as display filters. Recomputing findings with changed bounds is
an explicit analysis action with persisted parameters, not a hidden UI side effect.

**Acceptance:** directions and order match sources; totals use exact arithmetic
and never combine currencies without a supported conversion; no invented edges;
limited results expose truncation; keyboard users can inspect every shown link.

## 6. Ownership explorer — P1

**User value:** inspect how a person may hold an indirect interest and where a
declaration differs from supplied ownership records.

**Flow:** choose entity → inspect ownership paths → open percentage derivation
→ compare declared owner → inspect relationship records and document evidence.

**Proposed behavior:** ownership graph and path table; direct/indirect interests;
step-by-step multiplication; declaration comparison; unknown percentages,
cycles, overlap and depth limits visible beside the result. Distinguish a source
relationship from an inferred identity candidate.

**Existing foundation:** ownership graph, `entity_analysis`, deterministic
percentage calculations and declaration discrepancy evidence.

**Required extension:** typed ownership path presentation and precise linkage
to extracted declaration evidence when available. Verify what each tool payload
actually supports before adding a displayed combined-interest calculation.

**Acceptance:** calculations match Decimal-backed results; null stays unknown;
overlapping paths are not double-counted; cycles/incompleteness do not produce
confident ownership claims; label candidate beneficial ownership under demo
policy rather than jurisdictional legal UBO status.

## 7. Document comparison — P1

**User value:** inspect discrepancies in their original document context.

**Flow:** choose two documents for a supported subject → compare fields → select
a discrepancy → open the relevant page/anchor in each available document.

**Proposed behavior:** side-by-side PDFs on desktop, sequential panels on mobile;
raw and normalized fields; extraction confidence; matched, conflicting, missing
and low-confidence states; comparison against supplied entity declarations.

**Existing foundation:** original PDF routes, extraction fields and page/text
anchors, declared-field and cross-document comparisons.

**Required extension:** document viewer, comparable field model and reliable
anchor mapping. Text offsets are not automatically bounding boxes. Where exact
visual regions cannot be resolved, show page and text excerpts explicitly rather
than drawing a guessed highlight. Cross-document mismatch payloads may require
links back to each extraction field to recover page/anchor lineage.

**Acceptance:** every displayed value resolves to extraction/source evidence;
low confidence remains unresolved; benign formatting normalization is visible;
page links are correct; absent anchors have a clear fallback; OCR discrepancy
is never presented as proof of document forgery.

## 8. Actionable follow-up — P1

**User value:** turn an unresolved question into a bounded, recorded next step.

**Flow:** select a question or transaction reason → choose a suggested check →
review scope/parameters → execute allowed analysis or add a human note → inspect
linked results → record whether the question is resolved or still open.

**Proposed behavior:** case-linked task with originating evidence/question,
requested check, lifecycle, result references and human rationale. Distinguish
automated evidence checks from tasks requiring an investigator to obtain missing
information. If information is unavailable in the demo, say so.

**Existing foundation:** unresolved report questions, specialist tools and
immutable `needs_follow_up` report disposition.

**Required extension:** follow-up records, scoped APIs, idempotency, allowed
actions and linked child execution artifacts. Reuse deadlines, usage reservations
and session isolation; do not start unmanaged background work or retry forever.
Changed analysis/report content requires a new immutable artifact and review.

**Acceptance:** repeated submission does not duplicate execution; tasks survive
restart; action results cite sources; failure/gaps persist; prior approvals stay
intact; requesting follow-up alone does not run chargeable model calls.

## 9. Case Q&A — P2

**User value:** ask questions about supplied evidence and interpretations without
losing the ability to verify the answer.

**Flow:** ask a case/run-scoped question → receive cited answer → inspect sources
→ optionally request an explicit allowed follow-up for unanswered questions.

**Initial question families:** explain a finding, identify its supporting or
conflicting evidence, summarize missing information, compare supplied records,
and discuss legitimate alternatives. “Why was this transaction flagged?” links
to the deterministic reason panel rather than asking the model to invent reasons.

**Existing foundation:** structured evidence and Gemini synthesis; no interactive
question API currently exists.

**Required extension:** bounded retrieval over the selected run, answer/citation
contract, persisted question/answer scope and usage limits. Use deterministic
facts for quantitative answers, preserving the existing numeric-prose boundary.
Treat question/document text as untrusted input; no arbitrary SQL, URL fetches,
external data joins, or implicit case disposition.

**Acceptance:** all factual answer statements have resolvable source support;
unknown answers abstain; cross-case evidence is rejected; adversarial requests
cannot widen tool access; costs and failures are visible; no silent new run.
Citation membership alone does not establish semantic support: inspect actual
answer claims in evaluation.

## 10. History and readable report export — P2

**User value:** recover prior work, understand what changed and share a verifiable
assessment with a reviewer.

**Flow:** open history → select run → inspect its snapshot/report/review → compare
two runs → export a readable report with source references.

**Proposed behavior:** session-owned run list with timestamps, completion/gaps,
review state and input identity; comparison by source/derivation semantics rather
than evidence list position; readable HTML/print/PDF export alongside current
JSON. Include findings, transaction explanations, alternatives, limitations,
coverage, reviewer assurance and report hash/version.

**Existing foundation:** stored runs, pinned case snapshots, immutable report and
review artifacts, run lookup and JSON export. Browser local storage remembers
one latest key per case; it is not a complete durable history index.

**Required extension:** server-owned session history index/query route and export
renderer. Do not enumerate another session's objects. Preserve source IDs,
snapshot identity and page locators in exports. Offline exports need included
permitted source excerpts or an explicit access limitation; session-bound URLs
alone do not make a report portable. Cross-user share links are a separate access
design decision and are not assumed here.

**Acceptance:** session owners recover authorized runs after reload; another
session cannot list/read them; report and review hashes remain intact; diffs
distinguish changed inputs from changed interpretation; exports retain synthetic
labels, numeric precision and limitations; expired access is explained.

## Options considered and recommendation

| Approach | Advantage | Main assumption | Fails first when | Switching cost |
|---|---|---|---|---|
| Screening-first | Clear false-positive demonstration and discoverable watchlist | Matching is the central demo story | Users need deep transaction and document work across all five scenarios | Moderate; retain screening views within the broader workspace |
| Evidence-first workspace, recommended | Reuses existing tools and creates a coherent inspect/explain/review flow | Existing evidence can be presented with adequate role, order and source semantics | Payload gaps or inconsistent selection/snapshot state undermine explanations | Low infrastructure cost; moderate UI and contract work |
| Chat-first copilot | Flexible entry point for user questions | Retrieval and semantic evidence support are strong enough | Answers look persuasive but cannot be reliably verified or exceed quotas | Higher runtime/evaluation cost; chat can remain a later secondary entry |

Recommend evidence-first with transaction explanations in the first tranche.
This directly addresses both user complaints: watchlist discoverability and
insufficient investigative depth. All ten groups remain in the proposal.

## Dependencies and suggested sequence

| Tranche | Feature scope | Dependencies and completion gate |
|---|---|---|
| Foundation | Watchlist & Screening; Source explorer; Finding cards; Why this transaction was flagged | Typed views, source inspector, snapshot context and evidence-role/order support; all displayed reasons resolve correctly |
| Investigation depth | Interactive money trail; Ownership explorer; Document comparison | Foundation selection/citations plus path and anchor lineage; graph and document controls match source evidence |
| Investigation continuity | Actionable follow-up | Immutable linked execution records, persistence, quotas and bounded actions; no approval overwrite or duplicate execution |
| Flexible access and delivery | Case Q&A; History and readable report export | Scoped retrieval/history, semantic answer evaluation and export lineage; enforce session privacy and usage boundaries |

History indexing can be introduced during continuity work so later features do
not depend on browser-only keys. Readable export can use foundation cards before
Q&A is complete. Follow-up and chat require separate runtime verification; a
successful frontend build alone cannot establish their correctness.

This is a dependency proposal, not an implementation schedule. Estimate capacity
against the remaining freeze window after an implementation plan is requested.
Document any proposed release cut explicitly; never silently drop feature groups.

## Cross-feature design and engineering boundaries

- Preserve the accepted white, near-black and emerald visual direction; use
  readable tables/cards and contextual drawers. Keep structured inspection the
  default and original JSON available when useful.
- Reuse record/evidence IDs, source inspector, exact-value formatting, filters
  and citation controls. Do not create competing representations of one finding.
- Differentiate synthetic source, observed fact, indicator, hypothesis, tool
  assessment and human decision. Never conflate verification with criminality.
- Preserve failed, empty, missing, low-confidence, truncated and incomplete
  states. Empty screening inputs differ from a completed check with no candidate.
- Keep rule parameters and versions inspectable. Display actual current demo
  parameters; changing a policy requires a recorded new analysis context.
- Prefer source-supported templates for reasons and facts; use Gemini for
  interpretation where it adds value. Reopening a panel should not spend tokens.
- Keep all APIs session/case/run scoped; treat model and document text as data.
  Do not expose evaluator ground truth through explorer, retrieval or exports.
- Run immutable review and conflict checks when adding candidate/task records.
  Back up before any persisted schema/data migration.
- Keep public demo inputs synthetic and preloaded. A real watchlist integration
  requires a separately authorized source/license decision.

## Validation strategy

Start with narrow analytics/schema checks for changed contracts, then UI flows,
model/tool integration where applicable, and full scenario evaluation when shared
evidence or runtime behavior changes. Record failures rather than weakening gates.

| Scope | Required checks |
|---|---|
| Transaction reasons | Correct target versus baseline attribution; ordered path mapping; altered amount/currency/time/direction; partial/truncated analysis; negative controls |
| Screening | Same-name/conflicting-identity, potential-match and missing-identity controls; distinct Sanctions/PEP categories; empty list behavior |
| Ownership | Exact indirect percentages, null percentages, cycles, overlap and incomplete paths |
| Documents | Correct values/pages/anchors, benign normalization, missing fields and low confidence |
| Sources/cards | Correct pinned snapshot, broken/missing source states, accessible selection, no ground truth leakage |
| Follow-up/history/review | Persistence after restart, idempotency, immutable prior decisions, concurrent conflict and cross-session denial |
| Q&A | Semantic source support, abstention, contradictions, numeric boundary, adversarial input and quota failures |
| Exports | Exact values, labels, evidence locators, correct report/review version and explained source-access limits |

Exercise all five required scenarios: layering, ownership discrepancy, screening
disambiguation, KYC inconsistency and circular transfers. Browser flows should
cover desktop/mobile, keyboard navigation, loading, empty, success, error and
reconnection states. Proposed success metrics are task completion and evidence
verification accuracy; no speed or detection improvement is claimed before a
measured comparison.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Transaction inherits suspicion merely by appearing in evidence refs | Explicit participant roles; target transaction IDs; separate context/baseline from indicators |
| Narrative exceeds the evidence | Render computed facts directly; validate citations and review semantic claims |
| More screens produce fragmented context | Shared source selection, consistent case/run identity and deep links |
| Policy or schema expansion changes existing conclusions | Preserve current semantics first; version intentional changes and evaluate controls |
| Anchors imply false precision | Resolve actual page/text/region mapping and disclose fallback |
| Follow-up/chat consume unbounded budget | Explicit execution, reservations, time/call caps and visible refusal/failure |
| History/share exposes another visitor's work | Server-side session ownership; no assumed public share URL |
| Full scope exceeds freeze capacity | Estimate by tranche and obtain an explicit release decision; keep full report scope |

## Owning documentation for later implementation

Update only affected owning surfaces when contracts or operational behavior
actually change. This report remains a proposed brainstorm record.

- [Prototype brief](../../docs/prototype-brief.md): accepted experience and scope.
- [Project context](../../docs/project-context.md): verified implementation status.
- [Data model](../../docs/data-model.md): explanation, candidate review, task and history contracts.
- [Architecture](../../docs/system-architecture.md): bounded follow-up/Q&A routes and persistence.
- [Evaluation design](../../docs/evaluation-design.md): attribution and semantic support gates.
- [Cloud setup](../../docs/cloud-setup.md): only if authorized work changes verified operational routes.
- [Previous visual delivery](design-261010-2110-supabase-workspace.md): existing design and recorded deployment evidence.

## Unresolved product decisions

These decisions do not block this report. Resolve them before dependent
implementation; they are not evidence that the proposed features already exist.

1. Should all ten groups be targeted before the freeze, or should release timing
   follow the suggested tranches? Recommended: estimate tranches before committing.
2. Should candidate-level human assessments persist independently of report
   disposition? Recommended: yes, with explicit scope and immutable history.
3. Should follow-up initially run existing bounded checks only, or support new
   input collection? Recommended: existing checks and investigator notes; new
   input ingestion needs a separate access and data-handling design.
4. Which readable export is needed first: printable HTML or generated PDF?
   Recommended: printable HTML plus JSON, followed by PDF if sharing requires it.
5. Should shared reports be offline exports or authenticated links?
   Recommended: labeled offline exports initially; do not expose session-owned runs.
