# M01 — Local integrated readiness

## Decision

`READY` — M01 local integrated readiness passed. This is not M02, production
readiness, a hosted approval, or a release `GO`.

The required network acceptance is separately classified
`environment-blocked`: this environment denies loopback socket binding. The
same integrated MCP boundary passed the in-process ASGI acceptance alternative;
no external HTTP pass is claimed.

## Integrated SHAs

- Base requested and audited: `6d5b34b47c834fed99a87f170890acdc2b17fb03`
  (clean detached worktree before integration).
- M01-A Core implementation already in the candidate: `15693072a1eb7708a73926e9db67396bbb01f17f`.
  The Core handoff records its amended delivery object as
  `bb54f215c0da78228cec1f2bdd79f6213133163b`.
- M01-B MCP candidate: `6d5b34b47c834fed99a87f170890acdc2b17fb03`.
- M01-C Experience artifact incorporated: `f214e08ef166bb443b9bb240709a789f1c795467`.
- M01-C corrected handoff incorporated: `f56b42d5b0fc8650bc1248b20f358c736d3f7084`.
- M01 Verification harness incorporated: `f1ff1c10f32d152800af108b1162b90562f9684d`.
- Local cherry-pick results: `e31709c`, `4ac554f`, `3a33167`.
- Final integrated candidate before this readiness handoff: `3a33167`.

The Experience adapter preserves the frozen eight M1 tool names and exposes
the public `/mcp` seam; restore/import and connection revoke remain explicit
local control seams, not additional MCP tools. No Core, MCP, UI, or
Verification semantics were reimplemented.

## Acceptance and focused evidence

| Command | Result |
| --- | --- |
| `pytest -q tests/contract/test_m1_http_contract.py tests/conformance/test_m1_portable_memory.py` | `4 failed`; all failures are `initialize: M1 HTTP endpoint is unavailable` before MCP session setup; classified environment-blocked, not a product finding |
| `./scripts/demo-m1-portable-memory --transport http` | exit `1`; redacted `status=RED` with zero counts because the external endpoint is unavailable |
| `pytest -q tests/contract/test_m1_http_transport.py` | PASS — 3 passed; in-process ASGI proof covers strict tools, authority rejection, capture/candidate exclusion, Inbox confirm, cross-space recall, tenant isolation, scoped revoke, forget, and tombstone restore blocking |
| `pytest -q tests/unit/test_m1_core.py tests/unit/test_domain.py tests/unit/test_application.py` | PASS — 23 passed |
| `pytest -q tests/contract/test_mcp_contract.py tests/unit/test_import_boundaries.py` | PASS — 14 passed |
| `cd apps/web && npm test` | PASS — 8 tests |
| `cd apps/web && npm run check` | PASS |
| `cd apps/web && npm run build` | PASS — `web build complete: dist/` |
| `python -m compileall -q src/omp tests/fixtures/m1_http.py scripts/demo-m1-portable-memory` | PASS |
| `git diff --check` | PASS |

The UI render/DOM contract alternative passed loading, empty, error, candidate,
confirmation/lifecycle, recall reason, revoke, forget and tombstone-result
states through the Web tests and build. The prior Experience handoff also
records static DOM inspection at the local preview route. No browser E2E pass is
claimed in this environment.

## Limitations

- Direct `socket.bind` is environment-blocked with
  `PermissionError: [Errno 1] Operation not permitted`; therefore the required
  black-box HTTP command and demo could not reach a listening server.
- PostgreSQL disposable runtime and browser E2E were not required for this
  local synthetic M01 boundary and are not inferred as passed.
- ASGI evidence is intentionally not relabeled as an external loopback or
  hosted pass.
- No push, PR, tag, deploy, release, M02 work, hosted identity, or production
  claim was made.

## Next step

Coordinator may consume this handoff as the M01 local integrated-readiness
boundary. Re-run the two network commands in an environment that permits the
local listener before making any external-transport claim.
