# MCP connector contract v1 — conformance foundation

**Status:** `implemented-hosted-mapping + local-synthetic-fixture`

This is a transport-neutral contract for the minimum connector journey used by
the original M03-W0 preflight. Its typed fixtures and local adapter remain in
`examples/connectors/` as deterministic conformance tests. The current private
staging MCP maps the memory operations to hosted Streamable HTTP and OAuth; the
fixture itself is still neither an endpoint nor an OAuth implementation. See
[`../../../CURRENT_STATE.md`](../../../CURRENT_STATE.md) for the deployed boundary.

The journey is:

1. grant explicit consent and record the connector scopes;
2. capture only when the caller has consent and `memory:write`;
3. preserve provenance supplied with the capture;
4. recall from another authorized synthetic client with a bounded reason;
5. make update and forget replays idempotent;
6. emit a revocation event and fail closed for the revoked connection; and
7. prove tenant isolation and missing-scope negative cases.

The machine-readable files are:

- [`capabilities.json`](./capabilities.json): operation/scope matrix and
  compatibility labels;
- [`requests.json`](./requests.json): request and response shape for the
  minimum journey; and
- [`events.json`](./events.json): the `connection.revoked` event shape.

## Boundary and labels

Inside the machine-readable fixture, `tested` still means tested against the
deterministic local adapter only. Provider and hosted compatibility claims must
come from separate end-to-end evidence recorded in the current-state and
support-matrix documents, never from these fixture labels.

The adapter uses opaque synthetic identifiers and fixed UTC timestamps. It does
not use secrets, PII, network calls, product imports, GCP paths, or hosted
credentials. `source_client` is fixture metadata, not proof of compatibility
with a client bearing that name.

## Scope semantics

Scopes are an authorization input, while consent is a separate explicit
retention decision. A valid scope never substitutes for consent. Revocation is
connection-scoped: revoking `conn-chatgpt-sim` must not revoke
`conn-claude-sim` in the same synthetic tenant. A different tenant must receive
zero results even when it has the same scopes.

The contract remains implementation-independent. Hosted mappings may evolve
without rewriting the fixture, provided their scope, consent, isolation,
idempotency and revocation semantics stay compatible.
