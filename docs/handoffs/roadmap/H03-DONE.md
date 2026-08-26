# H03 — Streamable HTTP local composition

Status: `DONE / local in-process contract only`

## Base and commits

- Assigned base SHA: `d3d56c7233346b9e37ed3b5d3bd2778984c559f5`
- Acceptance freeze: `7cb3589` (`docs: freeze H03 streamable HTTP acceptance`)
- Implementation artifact: `5a4d27f5bb523b2b6b5a79c6e81b933d917b3430`
- Delivery commit containing this handoff is reported by Git after commit.

## Paths

- `src/omp/server/streamable_http.py`
- `tests/contract/test_h03_streamable_http.py`
- `docs/handoffs/roadmap/H03-ACCEPTANCE.md`
- `docs/handoffs/roadmap/H03-DONE.md`
- `docs/roadmap_implementation.md` — only H03 changed from `[ ]` to `[x]`

## Current acceptance evidence

| Gate | Freshness | Result | Command/artifact |
| --- | --- | --- | --- |
| H03 acceptance | current | PASS | `pytest -q tests/contract/test_h03_streamable_http.py` — 2 passed |
| formatting/lint | current | PASS | `ruff format ...`; `ruff check src/omp/server/streamable_http.py tests/contract/test_h03_streamable_http.py` |
| syntax | current | PASS | `python3 -m py_compile` on the two changed Python files |
| diff hygiene | current | PASS | `git diff --check` |
| related hosted contracts | current | 10 passed, 2 environment-blocked | `pytest -q tests/contract/test_h03_streamable_http.py tests/contract/test_hosted_gateway.py tests/contract/test_cloud_http.py` |

The two blocked tests attempted to bind `127.0.0.1`; the sandbox returned
`PermissionError: [Errno 1] Operation not permitted`. They are not claimed as
passes and no socket/listener was used by H03.

## Claims

The delivered claim is limited to an in-process ASGI composition with one
exact `/mcp` route, no `/mcp/` redirect, JSON-RPC `initialize`, `tools/list`
and `tools/call`, session continuity/reconnect, request IDs, cancellation
propagation, adapter timeout handling, separate health/readiness, host
allowlist, and a rate-limit seam inherited from the shared adapter. Tenant and
owner are derived only from the injected verified `Principal`; caller fields
are rejected before dispatch.

No public endpoint, network listener, token verifier, unverified token,
provider, deploy, Terraform, OAuth/IdP, credential, external service, push,
PR, tag, release, or real data was used. Readiness is fail-closed by default
and health is not used as a readiness substitute.

## Rollback and blockers

Rollback is a local revert of the H03 commits; no external state exists.
The only remaining local verification gap is the environment's prohibition on
loopback socket binding in the pre-existing related tests. H04 owns OAuth/IdP
and is outside this package.
