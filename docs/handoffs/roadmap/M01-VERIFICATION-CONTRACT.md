# M01 — Verification contract handoff

Status: `DONE` for the Verification harness; baseline product result remains
`RED`. This handoff is not an M1 readiness claim, an integration approval or a
release `GO`.

## Executable boundary

- Baseline/contract SHA exercised: `3b9cb40c4c6812237c37ab073586463f98cff000`.
- Frozen contract: [`M01-CORE-CONTRACT.md`](M01-CORE-CONTRACT.md).
- Acceptance transport: authenticated MCP Streamable HTTP at `/mcp`.
- Deliverables:
  - `tests/fixtures/m1_http.py`
  - `tests/contract/test_m1_http_contract.py`
  - `tests/conformance/test_m1_portable_memory.py`
  - `scripts/demo-m1-portable-memory`

The fixture is synthetic and verification-owned. It imports no product domain,
application or repository code. The three principals are deterministic:
`chatgpt-sim`/`user-a`/`tenant-a`, `claude-sim`/`user-a`/`tenant-a`, and
`chatgpt-sim-b`/`user-b`/`tenant-b`. Tokens are supplied by the local verifier
through `M1_TOKEN_CHATGPT_SIM`, `M1_TOKEN_CLAUDE_SIM` and
`M1_TOKEN_CHATGPT_SIM_B`; fallback token strings are only local fixture
defaults and are never printed.

## Contract exercised

The focused conformance journey uses separate authenticated HTTP MCP sessions
and asserts the complete frozen sequence:

1. consented `memory.capture` of a `lesson` in `MBA` creates a `candidate`;
2. candidate is excluded from default recall and visible only in the owner's
   `memory.inbox.list`;
3. `memory.inbox.confirm` increments the version and preserves provenance and
   `capture_consent`;
4. Claude recalls from `Work` with `include_spaces=["MBA"]`, including source
   metadata and `reason_retrieved=explicit_cross_space_semantic_match`;
5. tenant B receives an empty successful recall and inbox;
6. a local HTTP revocation hook revokes only `conn-chatgpt-sim`, after which a
   new ChatGPT capture fails safely while Claude still recalls;
7. Claude forgets the memory, repeated forgets return `already_absent`, and a
   pre-forget synthetic export posted to the local restore/import hook is
   rejected as `restore_blocked_by_tombstone` or `skipped-tombstone`;
8. post-restore recall remains empty.

`memory.revoke` and `memory.restore` are intentionally not added as MCP tools:
they are not tools in the frozen §7.2 surface. For a future local M1 runner,
`M1_REVOKE_URL` must accept an authenticated `POST` with
`{"connection_id":"conn-chatgpt-sim","client":"chatgpt-sim"}`, and
`M1_RESTORE_URL` must accept the authenticated synthetic `omp.export.v0`
package produced by the fixture. These hooks are HTTP setup/control adapters,
not a second product implementation; all memory capture, inbox, recall and
forget evidence remains on `/mcp`.

The contract test also checks the exact eight M1 tool names, required fields,
`additionalProperties=false`, absence of caller-supplied tenant/owner/
connection/scope authority, and destructive/read-only/idempotent annotations.

## Commands and results

Static harness checks passed:

```text
ruff check tests/fixtures/m1_http.py tests/contract/test_m1_http_contract.py \
  tests/conformance/test_m1_portable_memory.py scripts/demo-m1-portable-memory
All checks passed!
python3 -m compileall -q <M1 harness paths>
PASS
```

Frozen focused command, run without an M1 HTTP service at the baseline:

```sh
pytest -q tests/contract/test_m1_http_contract.py \
  tests/conformance/test_m1_portable_memory.py
```

Result: `4 failed`. Every failure is the safe harness classification
`initialize: M1 HTTP endpoint is unavailable`; there was no collection or
fixture-store failure. This is expected baseline RED because the product
checkout has no M1 HTTP endpoint. A direct baseline inspection also advertised
only `memory.write`, `memory.search`, `memory.update` and `memory.forget`, not
the frozen M1 tool set.

Frozen demo command:

```sh
./scripts/demo-m1-portable-memory --transport http
```

Result: exit `1`, with redacted output containing only the synthetic scenario,
`status=RED`, and zero counts. The demo does not print lesson text, query,
memory IDs, tenant IDs, credentials or secrets.

## Unambiguous future GREEN criteria

On one clean delivered SHA, with `M1_HTTP_URL`, the three local verifier tokens,
`M1_REVOKE_URL` and `M1_RESTORE_URL` configured:

- the focused command reports `4 passed`;
- `./scripts/demo-m1-portable-memory --transport http` exits `0` and reports
  `status=PASS` with counts `candidate:1,recall:1,tenant_b:0,forgotten:1,restored:0`;
- the eight tools and exact strict schemas/annotations are discoverable;
- no candidate, tenant-A memory, revoked capture or forgotten memory leaks
  through any success/error response;
- Claude remains authorized after ChatGPT revocation, and tombstone restore
  cannot recreate the forgotten ID;
- demo output remains redacted under both PASS and RED paths.

The current RED result is intentionally not converted to `xfail` or `skip`:
future M1 implementation must turn the same black-box assertions green. No
M1 readiness, integration, production, hosted-provider or release claim is
made here.
