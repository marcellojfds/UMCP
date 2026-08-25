# M03-W1 — synthetic connector recipe handoff

**Status:** `recipe-delivered`

This handoff covers only the reproducible local recipe lane. It does not claim
M03 done, real client compatibility, hosted authentication, or release
readiness.

## Base and delivery

- Requested/base SHA: `e6071ebbb69cc40c903f101f438af19c06d73a0a`
  (`codex/m03-connector-contract`).
- Delivery artifact SHA: `79c559d7ea63d2ec0868871f5432b0901aa857d6`.
- Correction: the new commit changes only this handoff to record the factual
  delivery SHA; no recipe, fixture, adapter, test, or contract semantics
  change.
- Prior W0 handoff: [`M03-W0-CONNECTOR-CONTRACT.md`](M03-W0-CONNECTOR-CONTRACT.md).
- Roadmap boundary: M3 still requires real-client evidence; the roadmap order
  starts with a controlled project agent, then real client surfaces.

## Ownership

Only these paths changed:

- `examples/connectors/recipe.py`
- `examples/connectors/recipe.md`
- `examples/connectors/README.md` (minimal navigation reference)
- `tests/conformance/test_m03_connector_recipe.py`
- `docs/handoffs/roadmap/M03-CONNECTOR-RECIPE.md`

No `src/omp`, auth, database/migrations, GCP/IaC/Docker/GitHub workflow, deploy,
or v1 contract files were changed.

## Delivered

- An executable `python -m examples.connectors.recipe` journey using only the
  delivered typed fixtures and `SyntheticLocalAdapter`.
- Explicit consent with the v1 `explicit` mode and
  `user_requested_memory` reason.
- Per-role minimum scope derivation from the v1 operation matrix.
- Capture, same-tenant recall, update, forget, replay idempotency, provenance
  preservation, cross-tenant zero-result isolation, and connection-scoped
  revocation with a `connection.revoked` event.
- A conformance test that compares the recipe scope matrix to v1 and executes
  both the Python API and module entrypoint without network or secrets.

## Checks

| Check | Result |
| --- | --- |
| `pytest -q tests/conformance/test_m03_connector_contract.py tests/conformance/test_m03_connector_recipe.py` | PASS — 5 passed |
| `ruff check examples/connectors/recipe.py tests/conformance/test_m03_connector_recipe.py examples/connectors/fixtures.py examples/connectors/local_adapter.py tests/conformance/test_m03_connector_contract.py` | PASS |
| `python -m json.tool` for v1 capabilities, requests and events | PASS |
| `python -m examples.connectors.recipe` | PASS — deterministic JSON summary |
| `python -m compileall -q examples/connectors tests/conformance/test_m03_connector_recipe.py` | PASS |
| `git diff --check` | PASS |

No environment blocker was encountered for this synthetic, offline lane. Real
network, OAuth, hosted endpoint, SDK, and client validation were not attempted
because they are outside this lane, not because they passed.

## Explicit limits and next dependency

The `chatgpt-sim`, `claude-sim`, and `tenant-b-sim` labels remain synthetic
fixture identifiers. This work claims no OAuth, hosted endpoint, official SDK,
real ChatGPT/Claude/Gemini/client support, GCP/deployment evidence, or M03
completion. The recipe also does not establish durable storage, retry behavior
across processes, production authorization, or compatibility with the M02
implementation. A later M03 lane must map these logical operations to a real
boundary and independently verify auth, consent persistence, provenance,
idempotency, tenant isolation, and revoke propagation.
