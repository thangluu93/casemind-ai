# CaseMind AI: current project context

Updated 2026-10-11, Asia/Ho_Chi_Minh.

## Current state

The user authorized brainstorm, plan and implementation after authenticating
Google Cloud. The [execution plan](../plans/261009-2203-casemind-prototype/plan.md)
reuses the [prototype brief](prototype-brief.md), architecture and five scenarios.
A FastAPI/ADK backend, deterministic analytics, seeded synthetic generator,
React workspace, immutable reviews, cloud adapters and evaluation runner exist.
The repository is public; competition submission is a separate step.

Project `casemind-ai` (`251896792352`) has billing enabled. Dedicated Storage,
BigQuery, Document AI, Artifact Registry and Cloud Run resources exist. Actual
Gemini, BigQuery, Storage and Document AI calls succeeded. See
[cloud setup and cost policy](cloud-setup.md) for commands and operational routes.
Five live demo investigations and five browser investigation/review flows passed.
The release benchmark remains subject to the measured evaluation report; do not
infer real-world accuracy from generated templates.

## Workspace extension

The [accepted workspace plan](../plans/261010-2218-investigator-workspace-replan/plan.md)
adds all ten feature groups, including visible Watchlist navigation, deterministic
transaction reasons, new synthetic CSV/JSON/PDF follow-up, bounded Q&A and
JSON/HTML/PDF reports. These changes exist locally; the earlier deployed version
has not been updated by this session. See [workspace contracts](investigator-workspace.md)
and the [execution report](../plans/reports/cook-261011-1326-investigator-workspace.md)
for verification and remaining live GIS/provider/deployed-browser gates.
No cloud spending, configuration, deployment or publication was performed for
this extension. Prior successful live prototype calls do not verify these changes.

## Insights expansion (2026-10-18)

The [insights plan](../plans/261018-1536-workspace-insights-expansion/plan.md) adds
twelve groups: an evaluation scorecard, a guided demo, an embedded-instruction safety
control, typologies, a threshold what-if, change drivers with alternative checks,
Gemini challenge and RFI drafts, model-planned graph queries, replay, maker-checker
review, a triage queue and a bilingual HTML export. See
[workspace contracts](investigator-workspace.md#insights-advisories-and-second-review).
The local tests and the offline browser suite pass. It is deployed as Cloud Run
revision `casemind-ai-00010-q78` with live advisory checks; see the
[deployment record](cloud-setup.md#deployment-record-2026-10-18). The public
repository is https://github.com/thangluu93/casemind-ai.

## Confirmed constraints

Two builders, approximately four hours each per day; October 17 freeze and
October 18 submission. The latest user decision replaces the earlier $300-credit
assumption: optimize gross service usage to **less than 1,000,000 VND**.
Credit activation remains unverified and is unnecessary for the cost estimate.
Target 750,000 VND, alert ceiling 950,000 VND; alerts do not stop charges.

One Cloud Run container serves four ADK specialists and an orchestrator using
Gemini 3.1 Flash Lite, deterministic tools, BigQuery, Document AI and Storage.
The UI exposes the graph, original sources, timeline, hypotheses, uncertainties
and a human decision bound to an immutable report hash/version.
All inputs are visibly synthetic. Numerical facts appear in tool evidence;
model prose is interpretive and cannot include digits. Citation membership is
validated; semantic claim support still requires human review.

## Access and remaining work

Use `gcloud --configuration=casemind-ai ...`; the named configuration selects
only this project. Local SDK development uses CLI credentials in memory through
`CASEMIND_USE_GCLOUD=true`; no ADC file or token is copied into the repository.
Cloud Run uses the scoped `casemind-runtime` service identity.

IBM archive/schema validation and OpenSanctions public-use licensing remain
unresolved. Neither provider supplies the demo data. The repository is public and
an English deck and demo video were prepared on 2026-10-18; portal submission is
the user's action.
Check the current official portal for category, eligibility and exact deadline.
