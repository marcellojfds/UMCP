# Open Memory Protocol

Open Memory Protocol (OMP) is a modular, user-owned long-term memory core for
applications that need explicit memory lifecycle, provenance, retrieval, and
portable export/import. The core is organized as `domain -> application <-
adapters`; MCP, the Python SDK, and the CLI are thin interfaces over that core.

## Status

This repository is preparing the documentation for `open-memory-protocol`
`0.1.0a1`, an unreleased Alpha release candidate. The planned publication
channel is a GitHub Release only. No tag, GitHub Release, or PyPI publication
has been created by this session.

The supported path is local/self-hosted PostgreSQL 16 with pgvector and MCP
over stdio. The current embedding profile is local deterministic `hash/v1`
(dimension 64), but retrieval quality has not been established by the
available S04 evidence. The file-backed backend is an explicitly labelled demo
harness, not release or production evidence.

## What is available

- Four MCP tools: `memory.write`, `memory.search`, `memory.update`, and
  `memory.forget`.
- A thin Python SDK using the official MCP client over stdio.
- A local CLI for status, lifecycle operations, smoke checks, and versioned
  export/import.
- Strict request validation, owner-scoped repository operations, optimistic
  version checks, idempotency, transactional forget, and PostgreSQL E2E paths
  covered by the available Alpha handoffs.
- `omp.export.v0` owner-scoped export/import. Embeddings are omitted by
  default, but exports remain sensitive files.

These are implementation claims bounded by the evidence in the [privacy
claim matrix](docs/privacy.md), [threat model](docs/threat-model.md), [MCP
protocol](docs/protocol.md), and [Alpha handoffs](docs/handoffs/alpha/).

## Important limitations

OMP Alpha is not E2EE, zero knowledge, hosted auth, or a hosted multi-tenant
service. In local stdio composition, `owner_id` is supplied by the client and
trusted. It is a logical partition, not authentication or authorization; do
not expose this composition to untrusted users.

The operator or anyone with access to the database, process, exports, or
backups can read memory data. Content, provenance/evidence, relations,
exports, backups, and embeddings are sensitive; embeddings are not anonymous.
Forget removes the tested online database records transactionally, but does
not revoke copies already exported or retained in backups. The project makes
no scale claim.

The S04 retrieval report and S05 privacy/operations handoff are missing from
this checkout, so this RC is documented but not publication-ready. See the
[known issues](docs/known-issues.md).

## Quickstart: supported PostgreSQL path

Requires Python 3.11, Docker, and a local checkout.

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'

docker compose -f ops/postgres/compose.yaml up -d --wait
export OMP_DATABASE_URL='postgresql+asyncpg://omp_test:omp_test@127.0.0.1:55433/omp_test'
OMP_DATABASE_URL="$OMP_DATABASE_URL" alembic upgrade head

OMP_DATABASE_URL="$OMP_DATABASE_URL" OMP_BACKEND=postgres omp status --json
OMP_DATABASE_URL="$OMP_DATABASE_URL" OMP_BACKEND=postgres omp eval smoke --json
OMP_DATABASE_URL="$OMP_DATABASE_URL" PYTHONPATH=src \
  python examples/e2e_two_clients.py
```

The database is disposable and bound to loopback. Stop it when finished:

```bash
docker compose -f ops/postgres/compose.yaml down
```

For a no-PostgreSQL smoke, opt into the file backend explicitly:

```bash
python -m omp.cli --demo-backend --data-file /tmp/omp-demo.json status --json
python -m omp.cli --demo-backend --data-file /tmp/omp-demo.json eval smoke --json
```

The demo does not demonstrate PostgreSQL, multi-user isolation, privacy,
retrieval quality, or production readiness.

## Documentation

- [Installation](docs/installation.md)
- [MCP integration](docs/mcp.md)
- [Python SDK](docs/sdk.md)
- [CLI](docs/cli.md)
- [Support matrix](docs/support-matrix.md)
- [Known issues](docs/known-issues.md) and [roadmap](docs/roadmap.md)
- [Protocol reference](docs/protocol.md) and [memory model](docs/memory-model.md)
- [Privacy](docs/privacy.md), [threat model](docs/threat-model.md), and
  [eval plan](docs/EVALS_PLAN.md)
- [Local MCP runbook](docs/runbooks/mcp-local.md)

The release-facing documents are English. Some historical design records and
privacy baselines are currently Portuguese and remain linked as source
evidence.

## Development

```bash
./scripts/gate-fast
./scripts/gate-postgres
```

`gate-fast` runs Ruff, strict mypy, and unit/contract tests. `gate-postgres`
fails closed when PostgreSQL 16, pgvector, or the migration head is missing;
it runs the real integration and E2E suites without silent skips.

Read [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), and the
[Code of Conduct](CODE_OF_CONDUCT.md) before opening a change. The project is
licensed under [Apache-2.0](LICENSE).
