# Continuity, intake, identity and question implementation

Status: DONE_WITH_CONCERNS

Implemented new `auth.py`, `continuity.py`, `intake.py`, `case_qa.py` and owned test modules. Shared routes, models, provider adapters and manifests remain the integration owner's responsibility.

## APIs delivered

- `Sessions(store, secret, audience, allowlist, verifier=None)` verifies Google's signed credential, audience, issuer, expiry, subject allowlist and CSRF equality. `issue(owner, anonymous_session=None, previous=None)` persists claim proof and anonymous revocation mapping before rotation; `resolve`, `revoke`, `owns_run`, `bootstrap` supply server-backed authority and bounded legacy discovery without rewriting run bytes.
- `Operations(store, ledger).reserve(owner,type,key,snapshot_hash,report_hash,sources,parameters,bill=True)` creates immutable request authority, conflicts before quota, and projects quota/history before readiness. `begin` returns a fenced `ExecutionContext` with one absolute deadline; `check()` returns remaining seconds. `finish`, `recover`, `history` retain terminal outcomes, recover projection gaps and mark expired work interrupted without provider replay. State transitions have durable append-only event projections.
- `FollowUps.command(owner,id,key,expected_version,command)` persists immutable command envelope first; command and semantic version apply atomically in the CAS aggregate. Replays return saved results, including after the envelope-before-aggregate crash boundary. Return `version` is a semantic counter, never a GCS generation.
- `stage_stream` counts decoded chunks before disk writes, caps type/request/PDF counts and verified pages, and reserves the follow-up staged byte total through CAS. `promote_staged` verifies owner namespace and promotes exact originals; `sweep_staging` removes abandoned one-hour staging. Parsing requires explicit synthetic classification.
- `IntakeBatch`/`IntakeRecord` implement add and revision-bound supersede for all six typed source groups. Validation considers forward references over the entire accepted set, quarantines dependency closures and every duplicate stable ID, and preserves explicit reasons/original refs. `commit_child` verifies source objects, pins originals for inherited demo documents, hashes owner-bound v2 manifests, writes owner lookup and immutable intake/quarantine audit.
- `ask_question` binds owner, run, snapshot, report, normalized question and retrieval hashes. Numeric count, amounts, currency-separated totals, transaction facts and percentages bypass synthesis; reason requests use the deterministic reason builder. Unsupported questions abstain without provider quota. Other allowed families receive one injected bounded real-provider synthesis call; validation rejects prose digits, foreign citations and unsupported schema. No runtime mock fallback exists.

## Verification

`./.venv/bin/python -m pytest tests/test_intake_history.py tests/test_case_qa.py -q`: **15 passed**.

Ruff for the four new modules and two new test modules: **passed**.

Tests cover CSRF/audience checks, rotation and restart revocation, durable legacy claims, unchanged run bytes, foreign-run exclusion, changed-key conflicts before quota, expired leases without replay, command envelope crash recovery, semantic versions, forward references, dependency quarantine, duplicate conflicts, supersede revisions, chunked oversize rejection, immutable promotion/TTL cleanup, deterministic facts, model digit/citation checks, one-call synthesis, and zero provider reservations for deterministic/unsupported questions.

## Integration requirements and limitations

- Main must enforce same-origin writes, authenticated intake, owner-scoped parent/run resolution, and the `claimed-sessions/{sha256(anonymous_session)}` revocation map. Bootstrap requires a persisted old-session claim proof.
- Main/provider boundaries must call the shared execution context before every cloud/provider boundary and terminal write; cloud publication intent/job identity/reconciliation and actual Document AI page reservations are shared integration work.
- SourceMetadata needs optional locator/source-object fields to retain uploaded provenance in the pinned manifest; intake audit already retains them.
- Multipart decoding is not inside these modules. The integration owner selected raw streamed upload routes, where `stage_stream` sees decoded file bytes and applies counters before buffering.
- Live GIS/GCS/Gemini/Document AI and deployed browser checks remain release gates. No spending, deployment or publication occurred.

Verified GIS guidance: [Google server token verification](https://developers.google.com/identity/gsi/web/guides/verify-google-id-token), including Python `google.oauth2.id_token.verify_oauth2_token` and backend subject authority. Existing google-auth dependency provides the verifier; no additional auth package is required.

## Independent integration review and repairs

A second review of `main.py`, `workspace_routes.py` and the frontend scope handlers found concrete retry, ownership and numeric-question defects. Owned modules now provide the following fixes/helpers; route and frontend changes remain the controller's responsibility.

- `FollowUps.replay(..., normalized_request)` checks immutable request identity before work/version checks. `prepare(...)` serializes a pending command without advancing the semantic revision; same-key restarts resume and different keys conflict. `command` atomically clears preparation and refuses changes to parent run/report/snapshot/evidence/question bindings. `abandon` is an explicit preparation cancellation, not a rollback of immutable side effects.
- `stage_stream` accepts `idempotency_key`, `expected_version`, and `filename`; repeated identical raw file streams reuse the same descriptor/accounting. Changed bytes/metadata conflict before PDF preflight or quota. `discard_staged` removes object and accounting together.
- `Sessions.owner_scopes` exposes old artifact namespaces only through durable ownership proof. `bootstrap_all`, `index_run` and `run_history` provide bounded claim discovery and owner-prefix history projections without rewriting original runs.
- Exact numeric questions now count the requested record group, apply explicit account/direction scopes, abstain on unsupported numeric/date filters, and avoid matching `sum` inside `summary` or `count` inside `account`. Unknown input shapes fail clearly.

Controller findings: upload/commit version checks previously preceded replay; staged failures deleted bytes but retained quota accounting; commit side effects preceded a command reservation; execution did not persist follow-up status and could overwrite its parent `run_id` with a linked child run; claimed tasks/assessments/questions were looked up only in the new owner prefix; history repeatedly scanned the global run prefix; async Q&A answers could append to a newly selected run. These findings were sent to the controller with helper wiring APIs. Linked child identity must use `linked_run_id`, preserving the immutable parent binding.

Raw file upload is a conscious API boundary: one decoded CSV/JSON/PDF stream per request permits caps before file buffering; it does not use multipart. This differs from the accepted plan's transport detail while retaining the original file types, typed whole-batch commit and cumulative limits. The operational/API documentation must state this choice.

Latest owned verification: **21 tests passed**, Ruff passed. No real-provider calls were made.

## Final deterministic Q&A citation repair

Every deterministic fact now carries `source_refs`, also aggregated on the answer. Record refs use `{kind: "record", snapshot_hash, record_id, group}` and resolve against the pinned case source inventory. Group counts cite their own source group; currency totals cite only contributing currency rows; scoped account totals cite the selected direction/account rows; ownership percentages cite the stable relationship record. Real collected evidence IDs are included when their refs intersect contributing sources; missing evidence is never invented.

Zero-record facts cite a typed pinned inventory `{kind: "inventory", snapshot_hash, record_id: null, group, record_count, collection_hash, scope, truncated}`. Collections over two hundred expose bounded record links plus the complete selected collection's deterministic hash/count and an explicit truncation disclosure. Scope records account/entity IDs, direction and optional currency, permitting reconstruction from the pinned inventory.

Final focused verification: `tests/test_case_qa.py` **10 passed**, Ruff passed. Added tests prove all refs resolve in the exact snapshot, group counts use their actual groups, totals preserve currency/account scopes, percentages cite relationships, absent evidence stays absent, zero counts cite empty inventory and large collections remain bounded. Existing zero-provider-quota checks continue to pass.
