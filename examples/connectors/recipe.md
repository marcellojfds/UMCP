# Connector contract v1 recipe

This is a reproducible local recipe for the adapter-neutral MCP connector
contract v1. It runs only against the typed fixtures and deterministic
in-memory adapter already present in this directory. It does not connect to a
provider, use OAuth, call a network endpoint, load secrets, or exercise
`src/omp`.

## Run

From the repository root:

```bash
python -m examples.connectors.recipe
```

The command prints a deterministic JSON summary. The living specification is
`tests/conformance/test_m03_connector_recipe.py`.

## Journey

The recipe follows only the operations and shapes in
[`docs/contracts/mcp/v1/`](../../docs/contracts/mcp/v1/):

1. Narrow the delivered synthetic fixtures to the minimum scopes used by each
   role. The source connection needs `consent:grant`, `memory:write`, and
   `connection:revoke`; the same-tenant collaborator needs
   `consent:grant`, `memory:read`, `memory:write`, and `memory:delete`; the
   other tenant receives only `memory:read`.
2. Grant a consent record whose mode is `explicit` and whose reason is
   `user_requested_memory` to the source and collaborator connections.
3. Capture content with the consent ID, source connection provenance, and an
   idempotency key.
4. Recall it through the collaborator connection and assert the bounded
   retrieval reason and unchanged provenance.
5. Recall from the other tenant and assert zero results.
6. Update the memory, replay the same idempotency key, forget it, replay the
   forget, and assert `already_absent` for a new forget key.
7. Capture a second synthetic record, revoke only the source connection, and
   assert a `connection.revoked` event plus fail-closed source operations.
8. Recall through the collaborator again and assert that connection-scoped
   revocation did not revoke the other same-tenant connection or cross tenant
   isolation.

The labels `chatgpt-sim`, `claude-sim`, and `tenant-b-sim` are fixture
identifiers only. This recipe does not claim support for ChatGPT, Claude,
Gemini, any SDK, OAuth, a hosted endpoint, deployment, or M03 completion.
