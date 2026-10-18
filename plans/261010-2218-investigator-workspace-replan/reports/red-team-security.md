# Red-team security and fact-check review

## Scope

Reviewed the replan index and all six phase files against the current authentication, storage, cloud-document, investigation and API code, plus the intake/foundation research and prototype brief. This is a plan-only review: no implementation changes or test execution.

## Findings

### High — Sign-out cannot revoke a copied stateless authenticated session

**Plan location:** `phase-04-follow-up-intake-history.md:26-27,58`

**Concrete failure:** The plan requires a signed expiring cookie and says sign-out “ends authenticated authority,” but it does not require a server-side session record, revocation marker or identity epoch. Clearing a browser cookie does not invalidate a copied signed cookie; it remains usable until expiry. That token would continue to authorize uploaded originals, imported child snapshots and complete owner history. This matters during the anonymous-to-authenticated transition because the one-time claim changes artifact authority, while the current service treats the cookie value itself as the full bearer credential and checks no revocation state (`backend/casemind/main.py:39-42,77-80`).

**Suggested fix:** Amend Phase 4 to issue a high-entropy session identifier inside the signed cookie and persist an owner-bound session record with expiry and revocation/version state. Rotate the identifier on login and after an ownership claim; sign-out must revoke the server record before clearing the cookie. Add tests that replay a captured pre-login, pre-claim and pre-sign-out cookie and prove each is rejected, including after restart.

### High — Upload limits are enforced after the dangerous resource consumption point

**Plan location:** `phase-04-follow-up-intake-history.md:29-30,57,61,75`

**Concrete failure:** The plan gives per-format byte, row, document and page limits, but “stage originals before parsing” does not define a request-level or streaming byte boundary. A multipart implementation can buffer the complete body in memory or temporary storage before route validation, and staging can persist an oversized object before the advertised limit is checked. The current HTTP middleware performs origin checks but has no body limiter (`backend/casemind/main.py:37-49`), and the current local persistence adapter serializes complete values in memory before replacement (`backend/casemind/store.py:40-49`). An allowlisted user or malformed client can therefore exhaust instance memory, ephemeral disk or object storage without ever producing an accepted intake record.

**Suggested fix:** Specify a hard cumulative request limit and streaming intake algorithm: treat `Content-Length` only as an early rejection hint, count decoded multipart bytes while streaming, stop before exceeding per-file and per-follow-up totals, and write only to an uncommitted temporary object. Hash during the stream, atomically promote accepted bytes, and delete/expire incomplete objects. Test chunked requests without `Content-Length`, multipart overhead, aggregate limits across ten PDFs plus CSV/JSON, disconnects, and proof that an oversize request commits no catalog object.

### High — Same-origin inline rendering exposes users to active content in preserved PDF originals

**Plan location:** `phase-03-flow-ownership-documents.md:26-27,51,62`; `phase-04-follow-up-intake-history.md:29-30,61`; `phase-05-qa-exports.md:30,59,71`

**Concrete failure:** The plan correctly preserves exact uploaded PDF bytes, but Phase 3 only says to stream them with “safe headers” and use a browser viewer. A structurally valid PDF may contain JavaScript actions, launch actions, embedded files or active links; it can pass media-type, hash and page-count checks. The current route returns raw PDF bytes inline from the application origin with only a media type (`backend/casemind/main.py:121-145`), and the current UI opens that same-origin route in a new tab (`frontend/src/evidence-review.tsx:101-104`). Phase 4’s generic rejection of “executable” content does not define whether PDF actions are detected, and modifying the original would violate the byte-preservation contract.

**Suggested fix:** Keep the immutable original unchanged, but make its download route attachment-only with a conservative filename and response CSP/sandbox headers. For in-workspace comparison, render a separately hashed inert derivative (for example, server-rendered page images or a verified PDF renderer configured with scripting, actions, external fetches and attachments disabled) and retain lineage to the original object generation/hash. Add fixtures containing `/OpenAction`, JavaScript, launch actions, embedded files, external URIs, malformed cross-reference tables and oversized decompressed streams; verify originals remain downloadable while active behavior is never executed in the app origin.

### Medium — The GIS browser flow is underspecified against the existing cross-site write boundary

**Plan location:** `phase-04-follow-up-intake-history.md:26,57-58,75,81`

**Concrete failure:** The plan says `/api/auth/google` accepts a GIS credential with double-submit CSRF and that required GIS CSP origins will be added, but it does not choose a GIS callback mode. The existing middleware rejects every write whose `Sec-Fetch-Site` is `cross-site` or whose `Origin` differs from the application origin (`backend/casemind/main.py:43-48`). A GIS redirect/form POST from Google will therefore fail. A hurried implementation could “fix” login by exempting the auth route from the global check, accidentally widening the only current browser write boundary.

**Suggested fix:** Pin the browser contract in Phase 4. Prefer GIS JavaScript callback mode followed by a same-origin POST carrying the credential and matching CSRF cookie/body token, leaving the middleware rule intact. If redirect mode is required, define one exact auth-path/provider-origin exception and retain the double-submit, token audience/issuer/expiry and allowlisted-`sub` checks. Add negative tests for foreign origins, cross-site fetch metadata, missing/mismatched CSRF values and GIS origins on every non-auth write route.

## Areas without an evidenced plan blocker

- The Q&A plan removes tools by default, bounds retrieval/model use, routes numeric answers deterministically, stores failures immutably and includes prompt/document-injection and cross-run tests. Current citation validation is only membership-based (`backend/casemind/investigation.py:87-102`), but Phase 5 explicitly records that limitation and Phase 6 adds semantic-support grading before release readiness.
- Export handling specifies one pinned canonical view, context-aware HTML escaping, script-free HTML, text-only PDF primitives, safe filenames, owner checks and adversarial format tests. No additional plan-level injection defect was found.
- Ground truth remains outside runtime inputs and public bundles, with a packaging/import scan and zero-cloud offline path in Phase 6. This matches the repository invariant and `docs/data-model.md:82-89`.
- The plan preserves the corrected decision that uploaded bytes contain supplied synthetic prototype data; it does not claim support for personal or regulated real data.

## Unresolved questions

None for plan revision. The four findings can be resolved as explicit contracts and tests without changing the accepted feature scope, export formats or synthetic-input decision.

Status: DONE_WITH_CONCERNS
Summary: The six-phase plan is materially grounded, but it needs explicit contracts for revocable authenticated sessions, streaming/cumulative upload enforcement, inert handling of preserved PDF originals, and a GIS callback mode compatible with the existing cross-site write middleware.
Concerns/Blockers: The three High findings should be closed before implementation because they affect the trust boundary for authenticated uploads and owner-scoped evidence.
