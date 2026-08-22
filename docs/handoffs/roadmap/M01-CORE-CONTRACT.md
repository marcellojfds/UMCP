# M01 — Portable Memory Local: core contract

**Status:** `frozen-before-implementation`

**Contract owner:** Luna / roadmap lane

**Baseline audited:** `d5b2513ee0bab426f590ad092cbefcd21a9bc8e8`

**Scope:** local synthetic M1 only. This document opens the implementation
boundary for M1-A Core, M1-B tools/conformance, M1-C Experience and M1
Verification. It is not an implementation, integration, hosted approval,
production approval, release GO, or claim that any M1 capability already
works.

## 1. Frozen outcome and non-goals

M1 is complete only when two synthetic clients share one isolated local vault:
`chatgpt-sim` captures a consented lesson, the lesson is visible as a
candidate in the Memory Inbox, the user confirms it, `claude-sim` recalls it
with provenance and `reason_retrieved`, tenant B gets no result, revocation
blocks only the revoked connection, and forget followed by restore cannot
resurrect the memory.

The following are outside M1 and cannot be inferred from this contract:

- real ChatGPT, Claude, Gemini or consumer-client integrations;
- automatic full-conversation ingestion; MCP receives only arguments sent by a
  client;
- hosted identity-provider, OAuth-provider, KMS, paid service, real email,
  production data, deploy, push, PR, tag, release or holdout;
- E2EE/zero-knowledge claims, client-side encryption or production SLOs;
- concepts graph, consolidation workers, automatic contradiction resolution or
  a universal cross-space policy.

The existing `omp` namespace and `omp.mcp.v0` contract remain supported. M1
adds capabilities; it does not rename or silently change v0 fields.

## 2. Terms and trust boundary

| Term | Frozen meaning | Producer | Consumers |
| --- | --- | --- | --- |
| `tenant` | Synthetic isolation boundary. Tenant A and tenant B never share a vault. | Local HTTP composition / fixture | Authorization, repository, Verification |
| `user` / `owner` | The person owning the vault. `owner_id` is an internal application key; it is not a hosted identity claim. | Verified principal mapping (HTTP) or trusted local v0 adapter | Application services and storage |
| `connection` | One named client authorization, e.g. `chatgpt-sim`; it has scopes, capture policy and revocation state. | Local connection registry | MCP auth boundary, audit, Experience |
| `candidate` | A captured memory awaiting user review. It is not eligible for default recall. | `memory.capture` | Inbox list/confirm/edit/discard |
| `confirmed` | User-approved active memory eligible for recall under space policy. | `memory.inbox.confirm` | `memory.recall`, v0 active projection |
| `pinned` | User-highlighted confirmed memory; eligible for recall with the same space rules and higher presentation priority only. | `memory.pin` | `memory.recall`, Experience |
| `stale` | Memory whose freshness is uncertain; excluded from default recall until reviewed. | Explicit stale command or future freshness worker | Inbox/recall with explicit state filter |
| `provenance` | Where the memory came from and when; not permission. | Capture producer | Recall, Inbox, audit-safe UI |
| `consent` | Why retention was allowed for this capture. It is separate from provenance. | Connection policy or explicit user action | Capture gate, Inbox, audit |
| `reason_retrieved` | Short deterministic explanation of a returned result. It is not chain-of-thought and never contains the raw query. | Recall service | MCP response, Experience, Verification |

The producer/consumer rule is strict: transports never construct lifecycle
state, infer consent, or apply cross-space policy. They validate wire shape and
map to application commands. The application service owns policy and errors;
repositories persist the result; the UI and Verification consume the public
result only.

## 3. Canonical M1 memory contract

### 3.1 Entity fields

The M1 `Memory` keeps every M0 field and adds the following canonical
semantics. Fields marked required are required for new M1 capture, even if a
legacy v0 row has no value.

| Field | Type / constraint | M1 rule |
| --- | --- | --- |
| `id` | opaque UUID | Stable within the vault; never reused after forget. |
| `tenant_id` | trusted tenant identifier | Derived from the verified connection/principal in HTTP. Never accepted from a hosted request body. |
| `owner_id` | non-empty bounded string | Internal owner scope. In local stdio v0 it remains a trusted payload for compatibility only. |
| `content` | non-empty text | Normalized whitespace; no full transcript by default; secret/category policy rejects prohibited payloads. |
| `type` | existing enum plus `mental_note` | `mental_note` is a first-class type, not an untyped note or system instruction. |
| `importance`, `confidence` | `[0, 1]` | Existing defaults remain for v0; M1 capture uses the same defaults unless supplied. |
| `state` | `candidate`, `confirmed`, `pinned`, `stale`, `superseded`, `contradicted`, `archived` | M1 canonical lifecycle. `forgotten` is absence, never a content row. |
| `version` | positive integer | Every confirm/edit/pin/unpin/stale/update increments version and uses optimistic concurrency. |
| `space` | nullable bounded identifier | New M1 calls use an explicit space when context matters. `null` is the legacy/global space and is never treated as permission to see every space. |
| `provenance` | object in §3.2 | Required for new M1 capture and preserved in every version snapshot. |
| `capture_consent` | object in §3.3 | Required for new M1 capture; legacy v0 rows are marked `legacy_unverified`, never upgraded to explicit consent. |
| `embedding` | existing profile descriptor | Retrieval only uses a compatible configured profile; M1 does not change the profile migration policy. |
| `idempotency_key` | opaque bounded key | Write/capture replay is owner-scoped as in v0. Mutating M1 commands use the operation ledger. |

### 3.2 Provenance and source metadata

`provenance` is the origin record. It is not a transcript and not an
authorization grant.

```json
{
  "source_type": "conversation",
  "source_client": "chatgpt-sim",
  "source_connection_id": "conn-chatgpt-sim",
  "conversation_id": "conv-opaque-001",
  "message_id": "msg-opaque-007",
  "source_model": "model-opaque",
  "captured_at": "2026-08-22T12:00:00Z",
  "evidence": ["user-selected-excerpt-1"]
}
```

Rules:

- `source_client` and `captured_at` are required on new M1 captures;
  `source_type` is required and is `conversation` for the acceptance journey.
- `conversation_id`, `message_id`, `source_connection_id` and `source_model`
  are optional opaque identifiers. They are not emails, access tokens or raw
  prompts. Their absence is valid for a user-created or imported memory.
- `captured_at` is timezone-aware RFC 3339 normalized to UTC. It is the source
  capture time, not necessarily the database write time.
- `evidence` contains only a user-permitted reference or short excerpt. It is
  optional, bounded and deleted with the memory. The full source conversation
  is never stored by implication.
- Recall exposes `source_client`, available IDs, `source_type`, `captured_at`
  and bounded evidence according to the connection policy. It does not expose
  internal tenant keys, credentials or hidden telemetry.

### 3.3 Consent and reason

`capture_consent` is a separate persisted object:

```json
{
  "mode": "assisted",
  "consent_id": "consent-opaque-001",
  "reason_code": "user_requested_memory",
  "policy_version": "m1-local-1",
  "granted_at": "2026-08-22T12:00:00Z"
}
```

Allowed `mode` values are `manual`, `assisted`, `automatic` and
`legacy_unverified`. `disabled` is a connection policy that rejects capture;
it is not a successful consent record. Allowed M1 `reason_code` values are
`user_requested_memory`, `user_confirmed_inbox` and
`connection_policy_automatic`. An import uses `import_authorized`.

New `memory.capture` requires a non-empty opaque `consent_id`, a permitted
mode/reason, and a timezone-aware `granted_at`. `assisted` is the local
default: capture creates a candidate and never auto-confirms it. A connection
set to `disabled` or a user/category “do not remember” rule fails closed before
content persistence. Consent metadata is not a substitute for user identity;
identity and connection revocation are checked separately.

### 3.4 Mental notes

`mental_note` is an allowed `type` with the same versioning, provenance,
consent, forget and tenant/owner isolation rules as every other memory. It is
not returned by default recall unless it is `confirmed`/`pinned` and the caller
explicitly allows notes. The default for `mental_note` is:

- same-space only;
- no implicit cross-space propagation;
- no instruction authority: clients must treat it as user data, never as a
  system/developer instruction;
- visible in the Inbox and inspectable by the owner.

## 4. Lifecycle state machine

| From | To | Operation | Recall default | Notes |
| --- | --- | --- | --- | --- |
| absent | `candidate` | `memory.capture` | no | Requires provenance and consent. |
| `candidate` | `confirmed` | `memory.inbox.confirm` | yes | Optional edit is one atomic versioned operation. |
| `candidate` | absent | `memory.inbox.discard` | no | Content, versions and vectors are forgotten; no restore. |
| `confirmed` | `pinned` | `memory.pin` | yes | Presentation priority may change; semantic ranking does not gain an arbitrary score. |
| `pinned` | `confirmed` | `memory.pin` with `pinned=false` | yes | Idempotent no-op when already unpinned. |
| `confirmed`/`pinned` | `stale` | explicit stale mutation | no | Does not silently delete content. |
| `stale` | `confirmed`/`pinned` | confirm/review mutation | yes | Requires expected version. |
| `confirmed`/`pinned` | `superseded` | existing update relation | no | Existing M0 relation requirement remains. |
| `confirmed`/`pinned` | `contradicted` | existing update relation | no | Existing M0 relation requirement remains. |
| any non-forgotten state | `archived` | existing archive mutation | no | Explicit restore to `confirmed` is allowed only for archived data. |
| any persisted state | absent | `memory.forget` or discard | no | Terminal for the memory ID; forget is content-deleting and idempotent. |

`candidate` is never included in default recall. `stale`, `archived`,
`superseded` and `contradicted` are also excluded. A caller may request an
explicit state only if the connection has read scope and the policy allows it;
this does not make a candidate a confirmed memory.

The v0 `active` state is a wire compatibility alias for M1 `confirmed` and
`pinned`. A v0 search with its default `active` filter reads confirmed/pinned
memories only. A new M1 response always uses the canonical state. There is no
v0 representation of candidate, pinned or stale; v0 clients must not infer
those distinctions.

## 5. Spaces and cross-space policy

Spaces are logical policy labels, not separate cryptographic vaults. A space is
owned by the same tenant/user scope and has a connection-visible policy:

```text
space_policy = {
  default_recall: "same_space_only" | "explicit_allowlist",
  allowed_spaces: [space_id, ...],
  allow_global: boolean,
  allow_mental_notes_cross_space: boolean
}
```

Frozen rules:

1. Tenant and owner filtering happens before any space filtering.
2. `memory.recall` takes a `context_space`. Without an explicit
   `include_spaces`, only `context_space` is searched; `null` means the
   legacy/global space, not all spaces.
3. `include_spaces` is an explicit, bounded allowlist. Every included space
   must be allowed by the connection policy. A client cannot broaden policy by
   putting a space in its request.
4. Cross-space recall is permitted in M1 only when the connection policy is
   `explicit_allowlist` and the request names the source space. The acceptance
   journey uses context `Work` and explicit `include_spaces: ["MBA"]`.
5. A personal/workspace space never crosses implicitly. `mental_note` remains
   same-space unless both the explicit allowlist and
   `allow_mental_notes_cross_space` permit it.
6. `reason_retrieved` must identify the policy path. The acceptance result uses
   the stable value `explicit_cross_space_semantic_match`.

## 6. Application commands and errors

All commands below are transport-neutral dataclasses in
`omp.application.models`. The application service owns validation, policy,
idempotency and transactions. HTTP adapters supply a trusted principal;
local v0 adapters may supply the existing owner payload only in the explicitly
legacy local composition.

| Command/service | Required input | Result | Idempotency |
| --- | --- | --- | --- |
| `CaptureMemoryCommand` / `capture` | trusted tenant/owner/connection, content, type, space, provenance, consent, key | `CaptureMemoryResult(memory, created)`; state is `candidate` | Existing write fingerprint plus owner-scoped key; divergent replay is `idempotency_conflict`. |
| `ListInboxCommand` / `list_inbox` | trusted scope, optional space, bounded page | `InboxResult(candidates, next_cursor)`; candidate-only | Read-only; no content in logs. |
| `ConfirmCandidateCommand` / `confirm_candidate` | memory ID, expected version, optional content/type/space edit, actor reason, key | confirmed `Memory` snapshot | Fingerprint includes target/version/patch/reason, never raw ledger payload; replay returns original result version. |
| `PinMemoryCommand` / `pin` | memory ID, expected version, `pinned`, key | pinned/confirmed `Memory` snapshot | Operation-scoped idempotent replay. |
| `DiscardCandidateCommand` / `discard_candidate` | candidate ID, expected version, key, reason code | `DiscardResult(forgotten=true/false)` | Terminal content deletion; tombstone survives and blocks restore. |
| `RecallMemoryCommand` / `recall` | trusted scope, query, context space, optional explicit spaces/types/states, limit/threshold | `RecallResult(items, count, profile)` | Read-only; no caller-supplied owner/tenant in HTTP. |
| existing `UpdateMemoryCommand` / `update` | existing v0 fields plus M1 provenance/state fields | versioned `Memory` | Existing `expected_version` and operation ledger semantics remain. |
| existing `ForgetMemoryCommand` / `forget` | memory ID, reason code, key | `ForgetMemoryResult(memory_id, forgotten)` | First call removes content; repeats return absent; ledger/tombstone metadata contains no content. |

M1 errors have stable internal codes: `validation_error`, `not_found`,
`version_conflict`, `invalid_state_transition`, `idempotency_conflict`,
`idempotency_in_progress`, `consent_required`, `capture_disabled`,
`connection_revoked`, `scope_denied`, `space_forbidden`, `restore_blocked_by_tombstone`,
`relation_conflict`, and `storage_error`. Public MCP errors may collapse
internal detail, but must preserve safe code class, retryability and request ID.
They never include content, query, provenance payload, owner/tenant IDs,
credentials or stack traces.

Concurrent mutation rules:

- all versioned state changes use `expected_version`, except first capture;
- terminal deletion uses owner/tenant scope plus idempotency and tombstone
  semantics rather than a version precondition;
- a stale version returns `version_conflict` and performs no partial mutation;
- relation/state changes and the version snapshot commit atomically;
- a failed mutation rolls back its idempotency claim;
- identical replay returns the original result snapshot, not the newer current
  snapshot;
- a different payload under the same scoped key returns
  `idempotency_conflict`.

## 7. MCP M1-B contract

### 7.1 Protocol and transport

M1-B exposes a local authenticated MCP HTTP surface at `/mcp` using the
Streamable HTTP adapter and the official MCP runtime already used by the
project. The M1 capability identifier is `omp.mcp.m1`. The existing stdio
`omp.mcp.v0` profile remains available for compatibility and keeps exactly its
four existing tools and strict schemas. Both profiles call the same
application services; no business logic is duplicated in a transport.

The HTTP profile derives `tenant_id`, `owner_id`, `connection_id` and granted
scopes from a verified local-development principal. It rejects `owner_id`,
`tenant_id`, `connection_id` and `scopes` supplied as authority in tool
arguments. The local-development verifier is a test adapter, not a hosted
identity or production claim. Revocation is checked on every call.

### 7.2 Tools, arguments and outputs

| Tool | Required arguments | Output | Scope / annotation |
| --- | --- | --- | --- |
| `memory.capture` | `content`, `type`, `space`, `provenance`, `consent`, `idempotency_key` | `{memory, status}`; new state `candidate` | `memory:write`; `readOnlyHint=false`, `destructiveHint=false`, `idempotentHint=true` |
| `memory.inbox.list` | optional `space`, `limit`, `cursor` | `{candidates, count, next_cursor}` | `memory:read`; read-only |
| `memory.inbox.confirm` | `id`, `expected_version`, optional `patch`, `idempotency_key` | `{memory, status:"confirmed"}` | `memory:write`; non-destructive, idempotent |
| `memory.inbox.discard` | `id`, `expected_version`, `idempotency_key`, optional reason code | `{status:"forgotten"|"already_absent"}` | `memory:delete`; destructive, idempotent |
| `memory.pin` | `id`, `expected_version`, `pinned`, `idempotency_key` | `{memory, status}` | `memory:write`; non-destructive, idempotent |
| `memory.recall` | `query`, `context_space`, optional `include_spaces`, filters, limit, threshold | `{memories, count}`; each item includes provenance, space and reason | `memory:read`; `readOnlyHint=true`, `destructiveHint=false` |
| `memory.update` | existing `id`, `expected_version`, M1 patch/state fields, `idempotency_key` | `{memory, status:"updated"}` | `memory:write`; non-destructive, idempotent |
| `memory.forget` | existing `id`, `idempotency_key`, reason code | `{status:"forgotten"|"already_absent"}` | `memory:delete`; `destructiveHint=true`, idempotent |

All M1 schemas reject unknown fields, bound content/query/limits/timeouts, and
use request IDs and the `omp.mcp.m1` envelope. `memory.recall` returns only
confirmed/pinned results by default; an empty result is a successful response
with `count: 0`. `reason_retrieved` is bounded deterministic text/enum and
never a hidden reasoning trace.

Connection capture policy is enforced before the service call:

- `disabled`: `memory.capture` returns `capture_disabled` and persists nothing;
- `manual`: capture requires an explicit user-request reason;
- `assisted`: capture creates a candidate and requires Inbox confirmation;
- `automatic`: only categories allowed by policy may be confirmed automatically;
  M1 acceptance does not depend on this path.

The five baseline scopes remain the vocabulary: `memory:read`,
`memory:write`, `memory:delete`, `memory:export`, `connections:manage`.
M1 tools use only the first three. A revoked connection fails closed before
lookup and does not reveal whether a target memory exists. Revoking
`chatgpt-sim` does not revoke `claude-sim` when the latter has its own valid
connection and scopes.

## 8. Migration and backward compatibility

M1 implementation must be a forward migration from the current head (logical
revision `0008_m1_local_memory_contract`; the concrete revision ID may use the
repository's migration naming convention). It must be tested from zero to head,
upgrade-in-place from the current head, and restore/import with synthetic data.

The migration is additive and must provide:

1. expanded memory type/state validation for `mental_note`, `candidate`,
   `confirmed`, `pinned` and `stale`, mirrored in `memory_versions`;
2. provenance JSON compatibility for `source_client`,
   `source_connection_id`, `conversation_id`, `message_id`, `source_model`,
   `captured_at` and bounded evidence;
3. a `capture_consent` record/column or equivalent versioned JSON field;
4. connection policy/revocation and consent storage for the local HTTP
   composition, reusing the existing tenant control-plane shape where present;
5. operation-ledger support for confirm, pin and candidate discard while
   preserving existing v0 write/update/forget keys and metadata-only rules;
6. a content-free forget tombstone keyed by owner/tenant and memory ID. A
   tombstone is sufficient to block restore/import of the same ID; it contains
   no content, provenance, query, embedding or secret.

Backfill rules:

- existing `active` rows become canonical `confirmed` rows; the v0 adapter
  projects confirmed/pinned back to `active`;
- existing `superseded`, `contradicted` and `archived` states are preserved;
- existing nullable `space` remains the legacy/global space and is never
  broadened to all spaces;
- old provenance remains readable. Missing M1 source fields are represented as
  `source_client: "legacy-v0"` and `capture_consent.mode: "legacy_unverified"`,
  with no invented conversation/message IDs or claim of explicit consent;
- old v0 requests continue to validate exactly as before. A v0 write creates a
  confirmed-compatible memory, not a candidate, because changing that would
  break the v0 meaning of `memory.write`;
- no migration rewrites content into logs or keeps a forgotten snapshot.

Rollback is supported only on a disposable database before M1 data is created.
For a database containing M1 rows, use a forward fix or verified restore; never
drop new lifecycle/source/consent/tombstone data as an operational shortcut.

## 9. Synthetic fixtures and frozen acceptance scenario

The fixture is black-box and synthetic-only. It must create deterministic
identities/connections for:

| Fixture principal | Tenant | Scopes | Policy |
| --- | --- | --- | --- |
| `chatgpt-sim` / user A | `tenant-a` | read/write/delete | capture `assisted`; Work may explicitly include MBA |
| `claude-sim` / user A | `tenant-a` | read/write/delete | same vault; own revocation state |
| `chatgpt-sim-b` / user B | `tenant-b` | read/write/delete | no visibility into tenant A |

Canonical capture payload values are synthetic and stable:

- type `lesson`, space `MBA`;
- content meaning: “incentives mal designed make teams optimize the metric,
  not the outcome”;
- `source_client: chatgpt-sim`, `source_type: conversation`;
- opaque conversation/message IDs and a fixed UTC `captured_at`;
- `consent.mode: assisted`, `reason_code: user_requested_memory`;
- concepts may be fixture metadata, but are not a substitute for provenance.

The single acceptance scenario is:

1. Authenticate the three synthetic connections with tenant/user context.
2. `chatgpt-sim` calls `memory.capture`; assert `status=created`, state
   `candidate`, required provenance/source fields, consent, space `MBA`, and
   no default recall result.
3. `chatgpt-sim` calls `memory.inbox.list`; assert exactly that candidate is
   visible to the same owner/connection policy and not to tenant B.
4. Inbox confirmation calls `memory.inbox.confirm` with the candidate version;
   assert state `confirmed`, version increment, and no loss of provenance or
   consent.
5. `claude-sim` calls `memory.recall` with context `Work` and explicit
   `include_spaces=["MBA"]`; assert exactly one lesson, source client
   `chatgpt-sim`, space `MBA`, captured timestamp/opaque IDs, and
   `reason_retrieved=explicit_cross_space_semantic_match`.
6. `chatgpt-sim-b` performs the same recall; assert success with `count=0`
   and no existence/error distinction that leaks tenant A.
7. Revoke only `chatgpt-sim`; assert its new capture fails with a safe
   revocation/scope error and persists nothing.
8. Repeat the Claude recall; assert it still succeeds because Claude's
   connection is independent and valid.
9. Claude calls `memory.forget`; assert `forgotten`, then repeat with the same
   and a different idempotency key; assert `already_absent` and no second
   mutation.
10. Restore/import the synthetic pre-forget package; assert the content-free
    tombstone returns `restore_blocked_by_tombstone` (or the black-box
    equivalent `skipped-tombstone`), the memory ID is not recreated, and Claude
    recall remains empty.

The acceptance entrypoint is frozen as:

```sh
./scripts/demo-m1-portable-memory --transport http
```

Verification's focused black-box contract suite is frozen as:

```sh
pytest -q tests/contract/test_m1_http_contract.py \
  tests/conformance/test_m1_portable_memory.py
```

Those paths are M1 Verification deliverables and may be absent on this
contract-only baseline. Their absence here is not evidence that M1 passes.

Verification must run this through the M1 HTTP MCP boundary. Direct fixture
store assertions may validate setup/cleanup only; they cannot be acceptance
evidence for the product path. The demo prints only a synthetic scenario ID,
status and counts, never the lesson text, query, IDs, credentials or secrets.

## 10. Ownership, paths and dependencies

| Lane / producer | Owns in M1 | Consumes | Publishes for next lane |
| --- | --- | --- | --- |
| M01 contract (this handoff) | `docs/handoffs/roadmap/M01-CORE-CONTRACT.md` and the limited M01 progress heartbeat | M00-ready boundary, roadmap, vision, playbook, ADRs, current models | Frozen fields, state machine, tool names, acceptance and ownership boundary |
| M1-A Core / Terra | `src/omp/domain/**`, `src/omp/application/**`, `src/omp/adapters/postgres/**`, `migrations/**` and core fixtures/tests for lifecycle | This contract; v0 domain/application contracts; existing idempotency/forget ADR | Core handoff with migration SHA, commands, lifecycle/idempotency tests |
| M1-B Tools / Terra | `src/omp/adapters/mcp/**`, `src/omp/server/**`, M1 MCP schemas/annotations and HTTP conformance adapter | M1-A commands/results; this tool/scope contract; ADR 0010/0011 | Tool handoff with `tools/list`, scope-negative, HTTP black-box and v0 parity evidence |
| M1-C Experience / Luna | `apps/web/**` Inbox route/components/tests and UI-facing adapter contract | M1-B public schemas; candidate/provenance/reason semantics; no direct repository access | Experience handoff with Inbox confirm/edit/discard and recall-visible evidence |
| M1 Verification / Sol or independent verifier | `tests/conformance/**`, M1 fixture/demo and verification handoff | Frozen acceptance scenario; HTTP boundary; synthetic connection matrix | Verification handoff with current SHA, result, skips and no release claim |
| Integration / coordinator | merge/ref reconciliation only; no lane implementation | All lane handoffs and tested SHAs | `M01-INTEGRATED.md`; only this opens the next milestone contract |

No lane may edit another lane's owned paths to unblock itself. In particular,
Experience never calls repositories directly, Verification never replaces the
HTTP path with the fixture, and Core never changes UI acceptance criteria
without a contract update before implementation.

## 11. Parallelization trigger and gates

M1-A Core, M1-C Experience and M1 Verification may be dispatched in parallel
only after all of the following objective predicates are true on one tested
contract SHA:

- this file exists and contains the exact state/field/tool/error/acceptance
  definitions above;
- `GOAL-PROGRESS.md` records the M01 contract freeze and paths/dependencies;
- the baseline is verified as the declared worktree/SHA and the tree is clean
  before dispatch;
- M00 readiness is consumed as a predecessor, without reopening or editing a
  M00 handoff;
- Core owns domain/migration/application semantics, M1-B owns transport
  mapping, Experience owns UI, and Verification owns black-box evidence;
- the acceptance scenario has a single producer for each transition and a
  named consumer for each result;
- no human decision is needed for local M1. Human decisions remain required
  later for hosted providers, region, budget, production data and release.

Lane-specific entry/exit gates:

| Lane | Entry | Exit before integration |
| --- | --- | --- |
| M1-A Core | Contract frozen; v0 tests understood; no concurrent domain writer | Migration zero→head and upgrade pass; lifecycle, conflict, idempotency, forget/tombstone and v0 compatibility tests pass |
| M1-C Experience | M1-B schemas/statuses/provenance shapes frozen; local web boundary available | Inbox shows candidate source/reason/space; confirm/edit/discard changes the same application-backed memory seen by recall; browser limitation is classified honestly |
| M1 Verification | Contract frozen; synthetic fixture and HTTP test plan use exact tool names | One command runs the ten-step scenario via HTTP MCP, tenant B is zero, revocation is scoped, restore is tombstone-safe, output is redacted, and evidence is current on the delivered SHA |

Integration must reject a lane handoff that changes tool names, state mapping,
scope requirements, ownership paths or acceptance assertions without a new
contract revision and re-dispatch decision. `DONE` on the board means only that
the bounded contract/ lane handoff is delivered; `INTEGRATED` is not release
GO.

## 12. Contract blockers and residual risks

No human decision blocks this local contract. The following are intentionally
deferred decisions, not hidden assumptions: hosted IdP/provider/KMS/region/
budget; real-client connector support; production retention/SLOs; and public
brand/release claims.

Residual implementation risks for M1-A/B are explicit:

- the current source models do not yet contain the M1 fields/states/tools;
- current v0 schemas reject unknown M1 fields and must remain unchanged;
- the existing fixture is Verification-owned evidence and is not Core-backed
  product behavior;
- browser and dependency-audit capability may remain environment-blocked and
  must never be converted into a pass;
- the HTTP local-development verifier proves only the local auth boundary.

These risks are accepted as implementation work after this freeze. They do not
authorize a release, production or hosted claim.
