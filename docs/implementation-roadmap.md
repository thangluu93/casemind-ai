# Implementation roadmap

Sequenced 2026-10-09 (UTC+7). The user authorized implementation; current execution
state is tracked in [the implementation plan](../plans/261009-2203-casemind-prototype/plan.md).
See [project context](project-context.md) for verified application and cloud state.

The user specified two people, approximately four hours each per day, and then
updated the budget ceiling to less than 1,000,000 VND gross service usage. October 10–17 provides
about 64 person-hours under that per-person interpretation; October 18 is buffer.
Project/model/processor access has been verified. Credit eligibility remains
unverified; cost allowances are documented in [cloud setup](cloud-setup.md).

## Scope and dependencies

Deliver all five scenarios, four specialist domains and the orchestrator,
the evidence graph, source inspection, review workflow and reproducible evaluation.
Prioritize one complete vertical slice first; extending scenarios does not excuse
leaving the initial slice with placeholder tools or prewritten findings.

Dependency order: validated data contracts → real deterministic tools → live
model/tool integration → evidence verification → workspace/review → full
evaluation → deployment/submission. Document extraction can proceed alongside
transaction tools once the contracts are stable.

| Target date | Delivery and suggested ownership | Acceptance evidence |
|---|---|---|
| Oct 9 | Research and prototype design, completed in this package | Sources, alternatives, contracts, scenario matrix and unresolved assumptions recorded |
| Oct 10 | Cloud/data feasibility and contract setup; backend/data owner | Verify trial/project/regions; test Gemini function call and Document AI parse; acquire IBM sample and license manifest; freeze initial schemas |
| Oct 11 | First transaction investigation and generator; backend/data owner | Layering/cycle/structuring tools return real row references; source/label isolation passes; team formation completed |
| Oct 12 | Integrated ADK vertical slice and first Cloud Run deployment; AI/backend owner | Case inventory → plan → actual tools → live synthesis → validated draft on cloud; altered input changes output; deployment stays inside confirmed trial budget |
| Oct 13 | Entity, screening and document paths; AI/data owner | Hidden ownership, false-positive and document inconsistency scenarios run; uncertain cases abstain |
| Oct 14 | Investigation workspace and review; frontend owner | Timeline, graph, source panel and approve/reject/follow-up work; reviews persist and are bound to report version |
| Oct 15 | Held-out evaluation and corrective work; all builders | Metrics with counts, failures, ablation and usage; fix evidence and safety failures before visual polish |
| Oct 16 | Cloud Run operational verification; backend owner | Cold start, IAM, reconnect, restart and shared usage quota behavior tested; rollback/log routes recorded |
| Oct 17 | Submission freeze and rehearsal; all builders | Public repo checked for secrets/data licenses; deployed URL tested from fresh session; English PDF deck and video under 3 minutes ready |
| Oct 18 | Buffer, final portal check and submission; team owner | Submission accepted and receipt recorded; exact portal deadline checked rather than inferred |

Proposed split: builder A owns backend/data/AI; builder B owns UI/evaluation/demo.
Neither assignment identifies an actual person or delegates work to an agent.
Aim for A's 32 hours: setup/contracts 4, generator/analytics 8, ADK/domain
integration 10, cloud/reliability 6, fixes 4. Aim for B's 32 hours: evidence UI 14,
evaluation/control cases 8, review integration 4, submission/rehearsal 6.
This is tight: use one shared schema and one UI layout for all five scenarios,
and prioritize feasibility checks before polish. If integration exceeds the
allocation, surface the schedule trade-off instead of silently reducing scope.

## Suggested implementation boundaries

- Backend: Python/FastAPI, ADK runtime, typed schemas, source adapters,
  deterministic analytics, evidence/report validation and review API.
- Frontend: React/TypeScript, case selector, run timeline, graph, evidence panel,
  report and review controls. Avoid a chat-first interface.
- Data/evaluation: independent seed generator, watermarked PDFs, source
  manifests, hidden truth and benchmark runner.
- Deployment: one container, Cloud Run configuration, service identity and
  documented setup. Pick final file layout when scaffolding; no existing code
  conventions currently constrain it.

Proposed API surface: case inventory, start a scoped run with idempotency key,
read run/events, inspect scoped evidence, read immutable report, and submit a
version-bound review. Design stable request/response schemas before UI integration.
Agents have no access to the review-write operation.

## Risks and decision triggers

| Risk | Response | Boundary |
|---|---|---|
| IBM download or terms block ingestion | Continue independent synthetic case development; keep external benchmark gate visibly pending | Do not claim IBM validation was performed |
| OpenSanctions usage remains unclear | Use the independently generated watchlist for all public cases | Retain provider adapter design; disclose synthetic coverage |
| ADK integration blocks first live slice | Try the direct SDK bounded runtime with the same domain/tool contracts | Preserve actual specialist behavior; record why orchestration changed |
| Document AI extraction is unreliable | Improve synthetic form clarity, retain raw extraction and expose uncertain fields | Do not replace parsed fields with hidden ground truth |
| Work exceeds capacity | Resolve team/time or scope trade-off explicitly with the user | Do not silently drop requested scenarios |
| Model retirement or quota issue | Test the configured supported model and rerun affected evaluation | Never hide provider failure with a canned result |
| Run exceeds request budget | Reduce case size or tool scope with visible truncation; otherwise introduce a durable worker | No unmanaged background process or unbounded loop |

Rollback uses the last verified container revision and its compatible immutable
input/schema versions. Preserve current run/report artifacts. Do not edit data
to make a failing revision pass; back up before any database mutation.

## Demo storyboard (target 2 minutes 45 seconds)

- 0:00–0:20: explain the investigator's fragmented evidence problem and select
  the main synthetic case.
- 0:20–1:05: run the investigation live; show actual specialist/tool events.
- 1:05–1:40: inspect a money path, ownership discrepancy and document source.
- 1:40–2:05: show the separate similar-name screening control and its evidence.
- 2:05–2:30: review the report, missing information and human disposition.
- 2:30–2:45: show measured evaluation, Google Cloud architecture and limitations.

Preload inputs and test cold-start behavior before recording. Any previously
executed result shown is labeled with its run time; the video must still prove
a live end-to-end path. Do not imply unseen analysis completed instantly.

## Next steps and unresolved questions

Continue the versioned implementation plan and measured reliability/evaluation checks;
retain failed results and distinguish template accuracy from real-world validation.
Confirm portal eligibility/category and exact deadline. OpenSanctions licensing,
IBM archive/schema access and actual cloud quota remain pending.
