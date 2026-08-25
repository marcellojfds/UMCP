# Synthetic connector fixtures

This directory contains the M03-W0 local preflight adapter and typed fixtures.
It is deliberately independent of `src/omp`, web clients, SDKs, hosted auth,
OAuth, network endpoints and deployment paths.

Run the focused conformance test from the repository root:

```text
pytest -q tests/conformance/test_m03_connector_contract.py
```

The executable v1 journey is documented in [`recipe.md`](recipe.md) and runs
with `python -m examples.connectors.recipe`.

The fixtures use opaque IDs and fixed timestamps only. They are not client
compatibility shims: `chatgpt-sim`, `claude-sim`, and `tenant-b-sim` are labels
for synthetic principals used to test scope, isolation, provenance, lifecycle,
idempotency, and revocation behavior.
