# CLI

The `omp` command is a local SDK/admin tool. It starts the stdio MCP server;
it is not a hosted service or a replacement for an identity boundary.

## Status and smoke

```bash
OMP_DATABASE_URL='postgresql+asyncpg://...' OMP_BACKEND=postgres \
  omp status --json
OMP_DATABASE_URL='postgresql+asyncpg://...' OMP_BACKEND=postgres \
  omp eval smoke --json
```

## Memory lifecycle

```bash
omp memory write --owner-id owner-a --type insight \
  --content 'Synthetic memory only.' --idempotency-key write-1 --json
omp memory search --owner-id owner-a --query 'Synthetic memory' --limit 5 --json
omp memory update --owner-id owner-a --id MEMORY_ID --expected-version 1 \
  --importance 0.9 --idempotency-key update-1 --json
omp memory forget --owner-id owner-a --id MEMORY_ID \
  --idempotency-key forget-1 --json
```

The PostgreSQL backend is the default. `--demo-backend --data-file PATH` is a
deliberate file-backed harness and must be supplied for local demo use. A
`--data-file` without `--demo-backend` is rejected.

## Export/import

```bash
omp --json export /tmp/omp-export.json --owner-id owner-a
omp --json import --dry-run /tmp/omp-export.json
omp --json import /tmp/omp-export.json
```

The export format is `omp.export.v0`, owner-scoped, and omits embeddings by
default. The file, history, provenance, and relations are sensitive. Dry-run
validates without mutating; replay is idempotent. CLI exit codes are documented
in [`docs/runbooks/mcp-local.md`](runbooks/mcp-local.md).
