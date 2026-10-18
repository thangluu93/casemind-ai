# Red-team failure review

## Scope

Plan-only hostile review of the six-phase investigator workspace replan against the current store, API, cloud, investigation, reliability-test, and evaluator paths. No implementation was changed and no tests, lint, typecheck, or build were run.

## High findings

### 1. The owner lease can expire while the same execute request is still legitimately running

**Plan location:** Phase 4, **Auth, ownership and persistence contracts**, item 6 (`phase-04-follow-up-intake-history.md:31`), and **Implementation steps**, item 7 (`:63`).

The plan acquires an owner lease before publishing the child and then investigating, but gives no operation-wide deadline, renewal, or fencing rule. The current lease is fixed at 150 seconds (`backend/casemind/main.py:220-226`). Child publication may spend 45 seconds waiting for BigQuery (`backend/casemind/cloud.py:74-76`), after which investigation gets a separate 120-second timeout (`backend/casemind/investigation.py:105-107`). This valid path already exceeds the current lease before storage, PDF, and request overhead. A second execute can acquire the expired lease while the first still calls Document AI/Gemini, duplicating billable work and racing run, operation, and history state.

**Required correction:** Define one absolute deadline covering publication and investigation. Store a fencing generation in the lease, renew it by CAS while the operation is active, and verify the fence before each provider boundary and terminal state write. A duplicate must return the existing operation. Add a slow-publication test that crosses the old TTL and proves only one provider execution occurs.

### 2. Idempotency keys are not required to bind to the canonical request

**Plan location:** Phase 4, **Auth, ownership and persistence contracts**, item 3 (`phase-04-follow-up-intake-history.md:28`), and **Implementation steps**, item 7 (`:63`); Phase 5, **Q&A and export contracts**, item 1 (`phase-05-qa-exports.md:25`), and **Implementation steps**, item 4 (`:57`).

The plan says duplicates return the same operation, but does not require a conflict when the same key is reused with different input. The current precedent derives a run ID only from session, case, and key, then returns any existing run without checking the request (`backend/casemind/main.py:200-218`). Follow-up and Q&A add material payloads: parent/report hash, staged object set, expected version, and question. Reusing a key after editing any of these can silently return an artifact for the earlier request, which is a scope and evidence-integrity failure.

**Required correction:** Define `(owner, operation_type, idempotency_key) -> {canonical_request_hash, operation_id}`. The request hash must include the pinned parent/report identity and all behavior-affecting input. Equal hashes return the same operation; unequal hashes return 409 without consuming quota. Test sequential and concurrent key reuse with changed staged objects, expected version, report hash, and question.

### 3. The plan treats several independent CAS writes as one durable reservation boundary

**Plan location:** Phase 4, **Auth, ownership and persistence contracts**, items 6-7 (`phase-04-follow-up-intake-history.md:31-32`), and **Implementation steps**, items 3, 7, and 8 (`:59-64`).

The store provides CAS for one key at a time (`backend/casemind/store.py:14-16,88-97`), while the plan requires quota reservation, idempotency mapping, owner history slot, operation, and run state on different keys before provider work. It gives no write order or authoritative recovery root. The current start path already reserves quota and only then creates the run (`backend/casemind/main.py:230-240`); a crash in that window consumes capacity with no run to discover. The expanded sequence adds windows that can also leave an unindexed operation or a history item with no operation. “Recovery never replays providers” does not make these records discoverable.

**Required correction:** Make the immutable operation record the first durable write and the sole state-machine authority. Give it the canonical request hash, owner, quota class, history identity, fence, and explicit `reserving -> ready -> executing -> terminal` states. Quota and history are idempotent projections keyed by operation ID; provider work begins only after both confirm the same operation. Recovery starts from owner-indexed operation IDs and repairs metadata only, never invoking providers. Add crash injection after every write boundary and assert conservative quota, complete history, one operation, and zero restart provider calls.

## Medium findings

### 4. “Complete legacy history” exceeds what legacy records can prove after cookie loss

**Plan location:** Phase 4 **Goal** (`phase-04-follow-up-intake-history.md:14`), **Auth, ownership and persistence contracts**, items 2 and 7 (`:27,32`), and **Done** (`:94`).

Legacy runs store only the random anonymous session value (`backend/casemind/main.py:231-239`). That cookie is generated client-side for this service and expires after one day (`backend/casemind/main.py:39-57`). Existing tests prove recovery only when the exact cookie is restored and denial for a stranger (`tests/test_store_api.py:55-82`). A bounded scan cannot prove that an unclaimed run belongs to a Google subject after the cookie is cleared or expires. Marking bootstrap “complete” without scoping the claim would overstate history while any broader association would weaken authorization.

**Required correction:** Define completeness as `complete_for_actor`: current anonymous session runs plus runs durably claimed while that session proof still exists. During sign-in, finish the bounded scan and persist the old-session-to-sub claim before replacing authority. Unclaimable legacy runs remain inaccessible and must not count toward authenticated completeness. Add expiry/cleared-cookie, interrupted multi-page claim, replay, and cross-owner tests; the UI must identify the scoped completeness boundary without revealing other-owner metadata.

## Verified non-findings

- Phase 1 explicitly threads versioned snapshot identity through legacy hash callers and verifies v1 raw canonical bytes before adaptation (`phase-01-evidence-source-foundation.md:29,56`).
- Phase 1 and Phase 3 explicitly require imported PDF reads by exact object generation plus SHA-256 and forbid metadata regeneration fallback (`phase-01-evidence-source-foundation.md:28,31,57-59`; `phase-03-flow-ownership-documents.md:27`).
- Phase 4 orders child BigQuery publication and identity verification before investigation/tool query (`phase-04-follow-up-intake-history.md:21,31,63`).

## Unresolved questions

- None. These corrections can be applied within the accepted one-service, full-ten-feature scope.

Status: DONE
Summary: Four concrete failure paths remain: lease expiry can permit duplicate execution, idempotency keys can alias different requests, multi-key CAS writes lack a recoverable authority/order, and legacy-history completeness is overstated after anonymous-session proof is lost.
Concerns/Blockers: Findings 1-3 should block implementation approval until the plan defines the state/fencing/request-hash contracts and crash-boundary tests.
