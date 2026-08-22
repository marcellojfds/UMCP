# M01-B — MCP transport and local controls — DONE

Status: `DONE` for the bounded M01-B transport lane only. This handoff does
not claim M1 integration, readiness, release GO, hosted identity, or production
approval.

Base SHA: `15693072a1eb7708a73926e9db67396bbb01f17f`.

## Delivered

- Added the authenticated local MCP Streamable HTTP boundary at `/mcp` using
  the official MCP runtime.
- Added exactly the frozen eight M1 tools with strict schemas,
  `additionalProperties=false`, frozen required fields, and safe tool
  annotations.
- Added a local-development bearer-token registry deriving trusted tenant,
  owner, client, connection and scopes. Caller-supplied authority fields are
  absent from tool schemas; provenance connection metadata is checked against
  the trusted connection.
- Mapped all tools to `MemoryApplicationService`, with public memory results
  omitting internal owner/tenant authority and stable generic error envelopes.
- Added authenticated local HTTP controls at `/local/revoke` and
  `/local/restore` (with local aliases), without adding either control as an
  MCP tool. Revoke is connection-specific; restore rejects a tombstoned memory
  before any import path can recreate it.
- Added `python -m omp.server --m1-http` as the local entrypoint.

## Owned files

- `src/omp/adapters/mcp/http.py`
- `src/omp/adapters/mcp/__init__.py`
- `src/omp/server/official.py`
- `src/omp/server/__main__.py`
- `tests/contract/test_m1_http_transport.py`
- `docs/handoffs/roadmap/M01-MCP-DONE.md`

## Evidence

- `ruff check src/omp/adapters/mcp/http.py src/omp/server/official.py src/omp/server/__main__.py src/omp/adapters/mcp/__init__.py tests/contract/test_m1_http_transport.py`: passed.
- `python -m compileall -q src/omp`: passed.
- `PYTHONPATH=src pytest -q tests/contract/test_m1_http_transport.py`: 3 passed.
- `PYTHONPATH=src pytest -q tests/contract/test_mcp_contract.py tests/unit/test_m1_core.py tests/unit/test_import_boundaries.py`: 16 passed.
- Re-runnable ASGI proof over the official Streamable HTTP app exercised
  discovery, capture, candidate exclusion, inbox confirmation, cross-space
  recall, tenant isolation, scoped revoke, forget and tombstone-safe restore.
  The observed result was one recall for tenant A, zero for tenant B, Claude
  remained authorized after ChatGPT revoke, and restore returned
  `restore_blocked_by_tombstone`.
- Direct socket proof: `socket.bind=BLOCKED PermissionError: [Errno 1]
  Operation not permitted` in this sandbox. No loopback socket pass is claimed;
  ASGI transport evidence above is intentionally classified separately.

The Verification-owned black-box M1 harness is not modified by this lane. No
M1 readiness or integration conclusion is made here.
