# MCP connector contract v1 — local conformance preflight

**Status:** `local-synthetic-preflight`

This is a transport-neutral contract for the minimum connector journey used by
M03-W0 preflight. It is intentionally exercised by typed fixtures and a local
adapter in `examples/connectors/`; it is not a hosted endpoint or an OAuth
implementation.

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

`tested` means tested against the deterministic local adapter only. It does not
mean a real client or provider is supported. `not-tested` is an explicit list
of claims this preflight must not make: real ChatGPT/Claude/Gemini behavior,
OAuth or hosted authentication, network transport, M02 implementation
compatibility, production authorization, or deployment.

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

The contract is independent of the M02 implementation. M03 work may map these
operations to a real boundary later; that mapping is a dependency and is not
claimed by this preflight.
