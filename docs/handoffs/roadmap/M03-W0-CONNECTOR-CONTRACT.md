# M03-W0 — connector contract and local preflight handoff

**Status:** `preflight-delivered`
**Scope:** connector contract, typed synthetic fixtures, local adapter, and
focused conformance test only.

This handoff does not declare M03 complete, real clients supported, hosted auth
available, OAuth completed, an endpoint deployed, or a release approved.

## Delivered

- Added the adapter-neutral v1 contract under
  [`docs/contracts/mcp/v1/`](../../contracts/mcp/v1/): capability/scope matrix,
  request/response shapes, revoke event shape, and explicit compatibility
  labels.
- Added typed, non-sensitive fixtures and a deterministic local in-memory
  adapter under [`examples/connectors/`](../../../examples/connectors/).
- Added a focused journey under
  [`tests/conformance/test_m03_connector_contract.py`](../../../tests/conformance/test_m03_connector_contract.py)
  covering explicit consent, scopes, capture, provenance, recall reason,
  idempotent update/forget, tenant isolation, and connection-scoped revoke.
- Added only a navigation link from the v0 README.

## Verification

The delivered artifact commit is
`7f77314eb5e5268f041f28bae712b05b2c8a616b`, based directly on
`faeadafef8589e2f3ef17de88f04114a3e02b742`. This file is being corrected in a
single follow-up commit; no artifact files are changed by the correction.

| Check | Result |
| --- | --- |
| `git rev-parse HEAD` and base comparison | PASS — artifact `7f77314eb5e5268f041f28bae712b05b2c8a616b`; base `faeadafef8589e2f3ef17de88f04114a3e02b742` |
| `pytest -q tests/conformance/test_m03_connector_contract.py` | PASS — 3 passed |
| `python -m json.tool` for v1 JSON files | PASS — capabilities, requests and events |
| `ruff check examples/connectors tests/conformance/test_m03_connector_contract.py` | PASS |
| `git diff --check` | PASS |
| owned-path diff audit | PASS — 11 files, all within declared ownership |

## Explicit dependencies and limitations

- M03 real integration must map these logical operations to the actual M02
  boundary and must independently verify auth, scopes, consent persistence,
  provenance, idempotency, isolation, and revoke propagation.
- The local adapter does not import or exercise `src/omp`, apps/web, SDKs,
  migrations, GCP, Cloud Run, deployment, IaC, or workflows.
- `chatgpt-sim`, `claude-sim`, and `tenant-b-sim` are synthetic labels only;
  the preflight makes no compatibility or hosted OAuth claim.
- The fixed timestamps and opaque IDs are fixtures, not production audit
semantics. Network behavior, retries across processes, and durable storage
are not tested.
