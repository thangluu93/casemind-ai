# CaseMind AI prototype brief

Direction researched and implementation authorized on 2026-10-09 (Asia/Ho_Chi_Minh).
Current verified state is in [project context](project-context.md).

Build an investigation workspace that follows money, tests entity relationships,
compares documents, and produces a report with evidence a human can inspect.
Position CaseMind as an **AI-assisted financial crime investigator**. Autonomous
tool execution is useful; responsibility for case disposition remains human.

## Delivery contract

- **Outcome:** an actionable research and architecture package now, followed by
  a deployed end-to-end prototype for the BFSI theme of AI Builder Cup 2026.
- **Constraints:** use Google Cloud AI; preserve evidence provenance; compute
  amounts and graph facts deterministically; label synthetic inputs; never
  invent relationships between real entities; require human review. Plan for
  submission by October 18, with a freeze on October 17. The user has two
  builders at approximately four hours per person per day and project `casemind-ai`.
  The latest budget ceiling is less than 1,000,000 VND gross service usage.
  Credit eligibility remains unverified; see [cost policy](cloud-setup.md).
- **Non-goals:** production bank integration, jurisdiction-specific compliance
  certification, automatic account blocking or regulatory filing, and a full
  enterprise case-management platform. These boundaries do not remove the
  five requested investigation scenarios from the prototype design.
- **Acceptance criteria:** five runnable scenarios with ground truth; actual
  tool calls and live Gemini synthesis; every factual finding resolves to input
  evidence; human approval/rejection persists; evaluation separates analytics
  quality from language quality; a deployed link, public repository, English
  deck and short video satisfy the submission requirements.

## Competition evidence

The official [FAQ](https://aibuildercup.com/Faqs.html) requires an end-to-end
working cloud prototype, a deployed URL, a public GitHub repository, a deck,
and a video under three minutes. It lists teams of 2–4 eligible professionals,
entrepreneurs or startup members, age 21+, based in JAPAC; students are excluded.

The [challenge page](https://aibuildercup.com/themes.html) explicitly includes
BFSI and requires Google AI or supported agentic platforms with deployment on
Cloud Run or Firebase. Submission materials must be in English. The stated
judging weights are technical/GenAI 40%, impact 25%, innovation 25%, UX 10%.
Its later category list conflicts with its six theme headings; select BFSI
using the current submission portal and record any discrepancy before submitting.

The [public timeline](https://aibuildercup.com/) ends team formation on
October 11 and prototype submission on October 18, 2026. This research did not
inspect the logged-in portal or verify an exact closing time or credit grant.

## Approaches and trade-offs

| Approach | Strength | Load-bearing assumption | Fails first when |
|---|---|---|---|
| One tool-calling investigator | Fastest end-to-end path, few prompts | One role can consistently cover all domains | Domain omissions and prompt coupling undermine verification; does not satisfy the requested specialist architecture |
| Bounded ADK specialist workflow, recommended | Clear domain ownership, visible execution, shared typed evidence | Team can integrate one Python service and one UI before the deadline | Model/tool integration or UI work consumes the available build capacity |
| Distributed agent services with event-driven orchestration | Independent scaling and retries | Infrastructure capacity and time are available | Deployment, state consistency and IAM work displace demo completion |

**Better approach:** preserve the requested multi-agent architecture inside one
Cloud Run service, rather than deploy each agent separately. ADK documents
multi-agent workflows and Cloud Run deployment. The operational delta is one
deployable service and one evidence contract instead of distributed coordination.
The implementation follows this single-service boundary. Enterprise
components remain a documented evolution path, not a prerequisite.

## Prototype experience

The workspace follows the user-supplied Supabase-inspired design: white canvas,
near-black type, emerald primary action, hairline panels and dark source JSON.
Inter is self-hosted; styling adds no external font service.

1. Investigator selects one of five labeled synthetic cases and sees source
   coverage before running it.
2. A visible execution timeline shows the investigation plan, specialist/tool
   calls, durations, evidence counts and failures.
3. A directed graph distinguishes accounts, legal entities, individuals,
   transfers and ownership. Clicking a finding highlights only its cited edges.
4. An evidence panel opens the original transaction rows, ownership records,
   screening candidates, or document page and extracted field.
5. A draft report separates observations, indicators, hypotheses, alternative
   explanations and unresolved questions. Investigator approves, rejects or
   requests follow-up with a recorded reason.

The main demo investigates layering through several entities and checks an
ownership/document discrepancy. A second short demonstration disambiguates a
similar watchlist name. These demonstrate both discovery and restraint.
Do not show unsupported claims of time saved or production detection accuracy.

The expanded ten-feature navigation, including the visible Watchlist tab,
transaction explanations and new-data follow-up, is documented in
[investigator workspace](investigator-workspace.md). Its local implementation has
not yet passed the separately required live release gates.

## Navigation

- [Dataset and technology research](research-findings.md)
- [System and agent architecture](system-architecture.md)
- [Data and evidence contracts](data-model.md)
- [Scenarios and evaluation](evaluation-design.md)
- [Implementation roadmap](implementation-roadmap.md)

## Unresolved questions

- Can both builders sustain four hours each per day through the submission freeze?
- Credit eligibility remains unverified; cost controls do not depend on it.
- Is the team eligible and formed, and what does its submission portal require?
- Will an OpenSanctions license cover this public competition demo? The design
  retains synthetic screening fixtures until the intended use is clarified.
