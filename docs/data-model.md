# Data and evidence model

Design baseline, 2026-10-09. The implemented prototype schemas now live in
[models.py](../backend/casemind/models.py). The tables below retain the broader
design vocabulary; they do not assert that every proposed field is implemented.
See [workspace contracts](investigator-workspace.md#source-and-snapshot-contracts)
for versioned snapshots, source objects, actors and intake.

## Core records

Every record has `schema_version`, stable namespaced `id`, `case_id` where
applicable, and provenance. Never use a display name as an identifier.

| Record | Required domain fields |
|---|---|
| SourceSnapshot | `source_kind`, URL or generator identity, source version, retrieval time, license, content hash, approved usage |
| Entity | person/legal entity type, names/aliases, typed identifiers, country, optional dates, source references |
| Account | source bank ID, source account ID, owning entity reference, currency where known |
| Transaction | sender/receiver accounts, timestamp with zone, amount/currency sent and received, payment type, source row locator |
| Relationship | from/to entities, relationship type, optional ownership percentage, validity period, source reference, identity certainty |
| Document | entity reference, type, private object reference, hash, synthetic watermark, source snapshot |
| ExtractedField | document ID, raw and normalized value, field type, page/text span/bounding box, processor version, extraction confidence |
| WatchlistRecord | source snapshot, category (`sanctions` or `pep`), identifiers, aliases, listing status and relevant dates |
| ScreeningCandidate | subject/candidate IDs, similarity features, supporting and conflicting attributes, missing fields, matching version, disposition |
| Case | title, entity/account/document references, case input manifest hash, coverage inventory |
| Run | case/input hash, idempotency key, status, model/prompt/tool/policy versions, timestamps, usage and step events |
| Evidence | evidence type, source IDs/locators, derivation details, payload hash, run ID, verification status |
| Finding | observation/indicator/hypothesis, structured claim, supporting/refuting evidence IDs, limitations, review priority contribution |
| Report | immutable run-bound version, findings, unresolved questions, priority and policy version |
| Review | report version/hash, actor/session identity, action, reason, timestamp; actor assurance labeled as demo-session or authenticated |
| GroundTruth | generator/scenario version, seed, expected observations/paths/fields/dispositions; accessible to evaluation only |

Money uses decimal strings or integer minor units with currency scale, never
binary floating-point. Preserve original timestamps and normalize comparisons
to UTC. Null means unknown; absent ownership percentages cannot become zero.
Do not aggregate currencies without an explicit conversion method.

## Provenance and verification are separate axes

`source_kind` is `public_real`, `public_synthetic`, or `casemind_synthetic`.
Reasoning records also carry `claim_kind`: `observation`, `indicator`, or
`hypothesis`. `verification_status` is `unverified`, `source_supported`,
`contradicted`, or `inconclusive`.

Thus an IBM synthetic transaction can support a verified calculation while
remaining synthetic. A real watchlist record can be accurate while identity
matching remains inconclusive. Source-supported never means proven criminality.
Display all relevant labels in the UI and exported report.

## Evidence contract example

Illustrative design example only; this is not an executed result.

```json
{
  "schema_version": "1",
  "id": "ev:demo:flow-001",
  "case_id": "case:demo:001",
  "run_id": "run:demo:001",
  "source_kind": "casemind_synthetic",
  "claim_kind": "observation",
  "verification_status": "source_supported",
  "source_refs": [
    {"snapshot_id": "snapshot:demo:1", "record_id": "tx:demo:001"},
    {"snapshot_id": "snapshot:demo:1", "record_id": "tx:demo:002"}
  ],
  "derivation": {
    "tool": "trace_flows",
    "tool_version": "1",
    "parameters": {"max_hops": 3, "window_hours": 48}
  },
  "payload": {
    "ordered_transaction_ids": ["tx:demo:001", "tx:demo:002"],
    "currency": "USD",
    "limitations": ["Path connectivity does not establish fund identity"]
  }
}
```

Production schema validation also requires content hashes, resolved locators,
valid timestamps, permitted enums and scope membership. Every document claim
points to a page and field/span. Every computed claim points to tool version,
parameters and original rows. Hashes detect content changes; they do not prove
the underlying source is truthful.

## Synthetic Case Generator

Create coherent fictional individuals, companies, accounts, ownership edges,
transactions and watermarked KYC/KYB documents from a versioned seeded generator.
Generate normal background behavior and scenario-specific structures together.
Emit inputs and ground truth to separate paths with separate access policies.
Agents and deployed demo bundles cannot read expected findings or labels.

Use controlled fictional names/identifiers and an independently generated
watchlist. Do not copy real sanctions names into a fabricated crime narrative.
Public sources retain their own namespace and are not automatically joined to
fictional entities. Source adapters normalize contracts; normalization is not
permission to create cross-source identity links.

Keep IBM AML-Data as a separately labeled transaction benchmark. Any adaptation
retains original row lineage and license and is evaluated separately from
CaseMind integrated ground truth. Do not quietly relabel generated transactions
as IBM data. For real-to-real entity resolution, exact verified identifiers can
support links; fuzzy candidates require review before becoming graph edges.

Ownership calculation multiplies known percentages along acyclic paths and
can sum distinct non-overlapping interests. Flag cycles, missing percentages,
overlapping paths and incomplete registers. Report candidate beneficial owners
under a documented demo policy; do not infer jurisdictional legal UBO status.

## Persistence mapping

BigQuery stores normalized immutable snapshots of transactions, accounts,
entities and relationships, partitioned appropriately for bounded case queries.
Cloud Storage stores manifests, original documents, extracted results, evidence,
reports and reviews by case/run/version. A manifest references the complete
snapshot and object generations. Write new versions and compare object generation
when updating the manifest so concurrent reviews cannot silently overwrite.

Prototype case states: `ready`, `running`, `awaiting_review`, `approved`,
`rejected`, `needs_follow_up`; run outcomes also include `failed`, `interrupted`
and `completed_with_gaps`. Approval confirms a human disposition of a report,
not guilt. Missing tools or sources must appear as gaps in the report.
