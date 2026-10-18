# CaseMind AI

**An AI-assisted financial crime investigator built on Google Cloud.** CaseMind follows
money, tests ownership chains, compares customer documents and screens watchlists.
Specialist agents call deterministic tools, and every finding links back to source
records a human can inspect. Responsibility for the case disposition stays with a person.

- **Live prototype:** https://casemind-ai-q36bubsb3a-as.a.run.app
- **Theme:** AI Builder Cup 2026, Banking, Financial Services and Insurance (BFSI)
- **Data:** every person, company, transaction and document is fictional and visibly
  labeled as synthetic.

## Why

Anti-money-laundering investigators piece together evidence scattered across
transaction systems, corporate registries, KYC files and screening tools. The slow
part is assembling and verifying evidence, not writing the narrative. CaseMind
automates the assembly and keeps a human in charge of the decision.

## What it does

| Area | Capability |
|---|---|
| Investigation | An ADK orchestrator plans four specialists (transaction, entity, compliance, document) that run deterministic tools on a pinned, hashed snapshot. |
| Evidence | Each finding cites source records, tool parameters, coverage and limitations. Model prose is digit-free, so every number comes from a tool. |
| Money trail and replay | Directed, chronological transfers with exact decimal amounts, plus a time-ordered replay. |
| Ownership | Per-step percentages, path products, unknowns and cycles. No legal beneficial-owner conclusion is drawn. |
| Documents | Document AI extraction compared field by field with declared values, with page anchors. |
| Screening | Name similarity kept separate from identifier agreement; conflicting and missing identifiers stay visible. |
| Typologies | Recorded indicators mapped to typology categories as observed, not observed or not evaluated. |
| Challenge | Deterministic checks of the most common legitimate explanation, a ranked list of what would change the conclusion, and a cited Gemini counter-argument. |
| What-if | Re-run the rules with different thresholds and see which transactions would change classification. The report stays unchanged. |
| Graph query | Gemini turns a question into a bounded path query that the investigator reviews before it runs deterministically. |
| RFI drafts | Neutral requests for information drafted from the evidence gaps. Never sent automatically. |
| Human review | An immutable decision bound to the report hash, an optional maker-checker second review, and HTML, PDF and bilingual (Vietnamese/English) exports. |
| Safety | Document text that tries to instruct the model is detected and withheld from every model prompt; a dedicated control case demonstrates this. |
| Evaluation | An in-app scorecard of measured benchmark runs, with live and offline runs reported separately. |

## Architecture

One Cloud Run service serves the FastAPI API, the Google ADK runtime and the
React/TypeScript workspace. Gemini (`gemini-3.1-flash-lite`) plans and synthesizes;
deterministic Python tools compute amounts, paths and comparisons. BigQuery holds
pinned transaction snapshots, Cloud Storage holds immutable sources and reports,
and Document AI Form Parser reads the synthetic PDFs. Details are in
[system architecture](docs/system-architecture.md) and
[investigator workspace](docs/investigator-workspace.md).

## Measured results

From the template-generated synthetic benchmark ([evaluation design](docs/evaluation-design.md)):

| Run | Attempts | Label precision | Label recall | Citations in scope | Control false positives |
|---|---|---|---|---|---|
| Live Gemini + Google Cloud, held-out split | 90 of 90 completed | 87.5% | 87.5% | 100% | 0 of 45 |
| Offline deterministic analytics, all cases | 50 of 50 completed | 100% | 100% | 100% | 0 of 25 |

These numbers come from synthetic templates and are not evidence of real-world AML
accuracy. Citation membership does not prove that a claim is semantically supported,
so human review remains required. OCR quality was not measured.

## Run locally

```bash
python3.12 -m venv .venv && ./.venv/bin/pip install -e '.[dev]'
npm --prefix frontend ci && npm --prefix frontend run build
./.venv/bin/python -m pytest -q
PYTHONPATH=backend ./.venv/bin/uvicorn casemind.main:app --port 8080
```

Without Google Cloud configuration, the workspace and source records still load;
new investigations return 503 instead of a simulated result. Cloud setup, cost
controls and deployment are described in [cloud setup](docs/cloud-setup.md).

## Boundaries

- Synthetic data only. No production bank integration and no personal data.
- Indicators, sanctions or PEP candidates and typology matches do not establish
  criminality. CaseMind never blocks accounts, files reports or approves a case.
- Jurisdiction-specific compliance has not been certified.
