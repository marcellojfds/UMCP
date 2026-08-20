# Contributing

Thank you for helping improve Open Memory Protocol. The public documentation
language is English; technical design records may remain in Portuguese while
the project is in alpha.

## Before opening a change

Read the [protocol](docs/protocol.md), [memory model](docs/memory-model.md),
[privacy baseline](docs/privacy.md), [threat model](docs/threat-model.md), and
[support matrix](docs/support-matrix.md). Keep changes scoped and describe
which contract, claim, or limitation they affect.

Do not include real personal data, memory exports, credentials, or production
logs. Use synthetic fixtures and canaries. Never weaken owner scoping,
redaction, validation, or the explicit PostgreSQL gate to make a test pass.

## Local checks

Create a Python 3.11 environment and install development dependencies:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
./scripts/gate-fast
```

For PostgreSQL integration and E2E, use the disposable PostgreSQL 16 +
pgvector gate:

```bash
./scripts/gate-postgres
```

The gate must fail when PostgreSQL, pgvector, or the migration head is absent;
SQLite and silent skips are not release evidence. Check the relevant workflow
under [`.github/workflows`](.github/workflows/) before proposing CI changes.

## Pull requests

Explain the behavior change, tests run, documentation updates, compatibility
impact, and any known limitation. For retrieval changes, keep the frozen eval
corpus unchanged and follow [`docs/EVALS_PLAN.md`](docs/EVALS_PLAN.md). Do not
change thresholds or datasets to manufacture a green result.

For security-sensitive changes, use the process in [`SECURITY.md`](SECURITY.md)
instead of a public issue. By submitting a contribution, you agree that it is
provided under the repository's Apache-2.0 license unless a separate written
agreement says otherwise.
