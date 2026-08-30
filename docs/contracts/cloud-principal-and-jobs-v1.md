# Cloud principal and worker-envelope contract v1

**Status:** principal boundary implemented in private staging; worker envelope remains a design contract.

The current hosted MCP validates its authenticated principal at the gateway and
exposes the memory tools described below. The signed asynchronous worker
envelope is retained as a future boundary; it is not part of the current MVP.
See [`../CURRENT_STATE.md`](../CURRENT_STATE.md) for deployed evidence and
known gaps.

## Principal

The gateway alone constructs this immutable value after token verification:

```text
Principal {
  subject_id: UUID; tenant_id: UUID; membership_id: UUID;
  scopes: set<Scope>; auth_method: "oidc" | "pat";
  credential_id: UUID; issued_at: instant; expires_at: instant;
  consent_id: UUID?; request_id: opaque-id
}
```

`subject_id`, `tenant_id`, `scopes` and credential identifiers are claims from
verified server-side records, not JSON tool arguments. Raw tokens, email and
display names are excluded. The core receives an internal command with this
principal; Cloud transport schemas have no `owner_id`.

| Tool | Classification | Required scope | Idempotency |
| --- | --- | --- | --- |
| `memory.search` | read-only | `memory:read` | not applicable |
| `memory.write` | write | `memory:write` | required |
| `memory.update` | write | `memory:write` | required |
| `memory.forget` | destructive | `memory:delete` | required |
| tenant export | sensitive read | `memory:export` | required request key |

## Signed worker envelope

```text
JobEnvelope {
  version: "umcp.job.v1"; job_id: UUID; kind: string;
  tenant_id: UUID; principal_id: UUID; credential_id: UUID?;
  payload_ref: opaque-id; dedupe_key: string; issued_at: instant;
  expires_at: instant; nonce: bytes; signature: bytes; key_id: string
}
```

The payload reference cannot contain content or credentials in logs. Workers
verify signature, expiry, nonce/replay state and tenant before setting local
database context. Unknown versions, expired jobs and missing context enter a
safe failed/DLQ state without retrying unauthorized work.
