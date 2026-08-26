# H03 — acceptance freeze

Frozen before implementation from base `d3d56c7233346b9e37ed3b5d3bd2778984c559f5`.

## Capability

An in-process ASGI composition serves the official Streamable HTTP JSON-RPC
methods at exactly `/mcp`, while stdio and local HTTP use the same application
adapter. The HTTP composition is fail-closed and has no listener, provider,
OAuth/IdP, credential issuer, or public route.

## Acceptance command

```text
pytest -q tests/contract/test_h03_streamable_http.py
```

The gate must prove `initialize`, `tools/list`, and `tools/call` at `/mcp`,
session continuity/reconnect, cancellation and timeout, request IDs, strict
host handling, separate truthful health/readiness, and rejection of any
caller-supplied tenant or owner. The service may receive tenant/owner only
from the verified `Principal` supplied by the composition.

## Paths and boundary

Owned paths are `src/omp/server/`, `src/omp/adapters/mcp/`, and
`tests/contract/test_h03_streamable_http.py`. Data is synthetic and in-process.
No public endpoint, unverified token, provider, deployment, Terraform,
OAuth/IdP, credential, external service, push, PR, tag, or release is in scope.

## Rollback

Revert the H03 commits; no external state is created.
