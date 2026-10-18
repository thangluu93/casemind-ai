# CaseMind prototype research delivery

2026-10-09, Asia/Ho_Chi_Minh. Status: research and brainstorm package complete;
implementation has not started. The user has two builders at about four hours
each per day, no cloud project, and a latest ceiling of $300 GCP free credit.
Trial eligibility and dataset access remain unresolved. No agents, servers or
cloud resources were started.

The recommendation is a bounded ADK specialist workflow in one Cloud Run
service, backed by Gemini, BigQuery, Document AI and Cloud Storage. It preserves
all five scenarios and human review, with deterministic calculations and scoped
evidence references. This is a proposed direction, not a user-approved build plan.

The [brief](../../docs/prototype-brief.md) owns the outcome, constraints,
non-goals, acceptance criteria and alternatives. The [research findings](../../docs/research-findings.md)
record primary sources and access/license limitations. [Architecture](../../docs/system-architecture.md),
[data model](../../docs/data-model.md), [evaluation](../../docs/evaluation-design.md)
and [roadmap](../../docs/implementation-roadmap.md) cover the remaining requested
research/design areas. Root [AGENTS.md](../../AGENTS.md) preserves conventions.

Verification: source pages checked; repository had only a context document and
was not initialized as Git. Documentation links and total line count are checked
after writing. No dataset/model/deployment benchmark result is claimed.

Next step: verify trial availability and run cloud/data feasibility checks during
implementation planning. Pending questions: sustained availability, project/quota,
OpenSanctions intended-use license, IBM archive/schema access and portal details.
