# CaseMind AI engineering context

This repository contains the prototype implementation and research/design documents.
Start with [prototype brief](docs/prototype-brief.md); it links the owning
research, architecture, data, evaluation and roadmap documents. Do not describe
proposed components or benchmark targets as implemented or measured.

## Product invariants

- Use Google Cloud AI for the competition prototype and retain human review.
- Preserve the five requested investigation scenarios and distinct domain roles.
- Compute numeric and graph facts using deterministic tools. Models plan,
  interpret and synthesize; they do not invent evidence or approve dispositions.
- Every factual finding references scoped, resolvable source evidence.
- Separate public real, public synthetic and CaseMind synthetic inputs from
  hypotheses and verification status. Never fabricate links between real entities.
- Keep ground truth out of runtime inputs, tools, retrieval and public demo bundles.
- Preserve uncertainty, contradictory identifiers and missing ownership data.
- Sanctions, PEP status and transaction indicators do not establish criminality.
- Synthetic documents and case screens must be visibly labeled.

## Development conventions

Follow user-provided development rules and current owning docs. Prefer KISS/DRY,
typed contracts, bounded tools and one deployable service until evidence justifies
additional infrastructure. Deliver requested scope; do not silently remove
features. Use kebab-case document names and language-native code naming.

Use the pinned dependencies in pyproject.toml and frontend/package-lock.json.
Verified cloud setup and operations are in docs/cloud-setup.md; tests live under
tests/ and frontend/e2e/. Pin framework/model versions after an actual integration check. Read
current official API docs when versions or endpoints may have changed.

Run focused analytics/schema tests first, then model/tool integration and full
scenario evaluation when shared contracts change. Preserve failing-check output;
fix behavior rather than weaken the gate. Use the scenario evaluation document
as the initial acceptance reference. Perform evidence/privacy review before
publishing a demo or repository.

Never commit secrets, credentials, dotenv files, personal data or unapproved
third-party archives. Use `gh` for GitHub operations. Back up before database
schema/data changes. Track processes by PID, command, port and workspace; reuse
existing processes and stop only those owned by the task when finished.

## Documentation and delivery

Write competition code/docs/submission materials in English. Keep plans/reports
in `plans/` and product/architecture docs in `docs/`. Use dated descriptive plan
names per the current session convention. Keep docs within the configured
800-line budget and link to owning schemas/scripts once they exist.

Read documents before changing them. Update only the smallest owning surface
when public behavior, contracts, setup or operational routes change. Record
verified deployment/log/rollback routes after authorization and deployment.
Research and roadmaps are stateful records, not claims of production readiness.

Do not start cloud spending, deployment or publication just because a design
mentions it. Reuse explicit user authorization when present. No cloud setup or
deployment was performed by the research session of 2026-10-09.
