# Installation

## Requirements

- Python 3.11;
- PostgreSQL 16 with the `vector` extension for the supported backend;
- `omp-migrate` migrations applied to `0004_semantic_source_version`; and
- Docker for the disposable local PostgreSQL gate.

## Install from a checkout

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
```

The package is named `open-memory-protocol` and the planned RC version is
`0.1.0a1`. For the verified Python 3.11/macOS arm64 environment, install with
`constraints/py311-macos-arm64.txt`; other platforms remain unverified.

## Start disposable PostgreSQL

From the repository root:

```bash
docker compose -f ops/postgres/compose.yaml up -d --wait
export OMP_DATABASE_URL='postgresql+asyncpg://omp_test:omp_test@127.0.0.1:55433/omp_test'
OMP_DATABASE_URL="$OMP_DATABASE_URL" alembic upgrade head
```

This compose file binds to loopback and uses a container tmpfs. It is for
development and verification, not a production backup or retention policy.
Run `docker compose -f ops/postgres/compose.yaml down` when finished.

## Verify the installation

```bash
OMP_DATABASE_URL="$OMP_DATABASE_URL" OMP_BACKEND=postgres omp status --json
OMP_DATABASE_URL="$OMP_DATABASE_URL" OMP_BACKEND=postgres omp eval smoke --json
OMP_DATABASE_URL="$OMP_DATABASE_URL" PYTHONPATH=src python examples/e2e_two_clients.py
```

The full database gate is `./scripts/gate-postgres`; it checks PostgreSQL 16,
pgvector, migration head, integration tests, E2E, and downgrade/upgrade.

The optional semantic runtime is deliberately separate and offline-only:

```bash
python -m pip install -e '.[semantic]'
export OMP_EMBEDDING_PROVIDER=e5
export OMP_EMBEDDING_PROFILE_ID=semantic
export OMP_EMBEDDING_PROFILE_VERSION=e5-small-v2-s09
export OMP_EMBEDDING_DIMENSION=384
export OMP_SEMANTIC_MODEL_ROOT=/secure/operator/cache/e5-small-v2
```

The model directory must already contain the exact pinned revision configured
by `OMP_SEMANTIC_MODEL_REVISION`; the runtime never downloads or falls back to
another provider.

## Explicit demo mode

For a file-backed smoke without PostgreSQL, every command must opt in:

```bash
python -m omp.cli --demo-backend --data-file /tmp/omp-demo.json status --json
python -m omp.cli --demo-backend --data-file /tmp/omp-demo.json eval smoke --json
```

This mode is not the supported release backend and must not be used to claim
PostgreSQL, privacy, retrieval, or multi-user readiness.
