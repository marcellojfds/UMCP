# M01-A Core Capture Domain — DONE

Status: `DONE` for the bounded Core lane only. This is not an M1 integrated
status, verification claim, release claim, or production/hosted approval.

Delivery commit object SHA: `bb54f215c0da78228cec1f2bdd79f6213133163b`.
The final single local commit containing this handoff is the amended commit
whose SHA is published with the board event below.
Base commit: `3b9cb40c4c6812237c37ab073586463f98cff000`

## Delivered

- Added canonical M1 memory states: `candidate`, `confirmed`, `pinned`, and
  `stale`, while retaining the v0 `active` compatibility state.
- Added `mental_note`, bounded source/provenance metadata, and versioned
  `CaptureConsent` with `manual`, `assisted`, `automatic`, and
  `legacy_unverified` modes.
- Added transport-neutral capture, Inbox list/confirm/discard, pin, recall,
  space policy, scope/revocation fail-closed checks, and deterministic
  `reason_retrieved` results.
- Added candidate-only default recall exclusion, same-space and explicit
  cross-space policy, tenant/owner filtering in the in-memory Core fixture,
  and mental-note recall opt-in.
- Extended operation idempotency for confirm/pin/discard, optimistic version
  checks, stable replay snapshots, and content-free tombstones that block
  import/restore.
- Added additive migration `0008_m1_local_memory_contract`: lifecycle/type
  checks, consent JSON, legacy-v0 backfill, connection capture policy/consent
  metadata, operation types, and `memory_tombstones`.
- Preserved v0 serialization and search semantics; `active` projects to the
  recall-eligible `confirmed`/`pinned` set after migration.

## Owned files

- `src/omp/domain/{types.py,memory.py,serialization.py,errors.py,__init__.py}`
- `src/omp/application/{models.py,ports.py,services.py,fakes.py,__init__.py}`
- `src/omp/adapters/postgres/{schema.py,repository.py}`
- `migrations/versions/0008_m1_local_memory_contract.py`
- `tests/unit/test_m1_core.py`

## Evidence

- `python -m compileall -q src/omp migrations`: passed.
- `ruff check src/omp/domain src/omp/application src/omp/adapters/postgres
  migrations/versions/0008_m1_local_memory_contract.py
  tests/unit/test_m1_core.py`: passed.
- `pytest -q tests/unit/test_domain.py tests/unit/test_application.py
  tests/unit/test_m1_core.py tests/unit/test_import_boundaries.py`: 25 passed.
- `alembic heads`: `0008_m1_local_memory_contract` is the single head.
- `alembic upgrade head --sql`: generated zero-to-head SQL including the M1
  columns, checks, policy metadata, and tombstone table.
- `pytest -q tests/integration/test_postgres_retrieval.py`: 18 skipped because
  disposable PostgreSQL/pgvector was unavailable in this environment.
- Full `pytest -q`: 101 passed, 19 skipped, 2 failures in pre-existing HTTP
  contract tests because the sandbox denies `socket.bind` with
  `PermissionError`; no HTTP/MCP files were changed by this lane.

## Interfaces for M1-B and M1-C

M1-B should map its transport schemas to these application models and methods:

- `CaptureMemoryCommand` → `MemoryApplicationService.capture`;
- `ListInboxCommand` → `list_inbox`;
- `ConfirmCandidateCommand` → `confirm_candidate`;
- `DiscardCandidateCommand` → `discard_candidate`;
- `PinMemoryCommand` → `pin`;
- `RecallMemoryCommand` → `recall`;
- existing `UpdateMemoryCommand`/`ForgetMemoryCommand` → `update`/`forget`.

Results expose `Memory` with `state`, `space`, `provenance`, and
`capture_consent`; recall returns `RecallResult.items` with bounded
`reason_retrieved`, profile identifiers, and count. Domain errors expose the
stable codes from `src/omp/domain/errors.py`, including
`connection_revoked`, `scope_denied`, `space_forbidden`,
`version_conflict`, `idempotency_conflict`, and
`restore_blocked_by_tombstone`.

M1-C should consume the Inbox result directly: candidates are visible only in
`InboxResult.candidates`; confirm/edit returns the versioned `Memory` snapshot;
discard is terminal; source display comes from `Memory.provenance`; consent
display comes from `Memory.capture_consent`; and recall presentation uses the
bounded `SearchMemoryItem.reason_retrieved`. UI must not access repositories or
infer authority from provenance.

## Limitations and handoff boundary

This lane intentionally does not implement MCP transports/schemas, HTTP local
authentication, web UI, black-box verification harness/demo, push/PR/tag,
deploy, hosted providers, or release claims. PostgreSQL runtime integration
requires a disposable PostgreSQL 16 + pgvector environment; the migration was
validated by generated SQL only here. M1-B/M1-C must preserve the frozen tool
names, scope mapping, tenant-derived authority, and acceptance assertions from
`M01-CORE-CONTRACT.md`.
