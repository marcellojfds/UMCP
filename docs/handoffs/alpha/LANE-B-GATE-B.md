# Lane B — Gate B checklist

**Status: GREEN — aprovado com evidência PostgreSQL + pgvector real.**

| Critério | Estado | Evidência |
|---|---|---|
| MCP oficial stdio | verde | `FastMCP`, `ClientSession`, `stdio_client`, E2E real |
| Quatro tools no servidor | verde | `initialize`, `tools/list`, `tools/call`, E2E real |
| Caminho Postgres + pgvector | verde | `pgvector/pgvector:pg16`, PostgreSQL 16.15 |
| Reinício e recuperação real | verde | novo processo oficial no E2E |
| E2E sem fake e sem skip | verde | `1 passed`, `OMP_REQUIRE_POSTGRES_TESTS=1` |
| Export/import Postgres | verde | ports reais, `omp.export.v0`, dry-run, import e replay |
| CLI default sem fake | verde | backend default `postgres`, sem fallback |
| Ruff Lane B | verde | `All checks passed` |
| mypy strict Lane B | verde | sem issues nos arquivos Lane B |
| Suite completa obrigatória | verde | `51 passed, 1 warning`, zero skips |
| Canary scan | verde | stderr/log artifact sem conteúdo-canário |

## Comandos de verificação

```bash
export OMP_TEST_DATABASE_URL='postgresql+asyncpg://...'
alembic upgrade head
OMP_REQUIRE_POSTGRES_TESTS=1 PYTHONPATH=src pytest -q tests/e2e
OMP_REQUIRE_POSTGRES_TESTS=1 PYTHONPATH=src pytest -q
```

O export foi owner-scoped, omitiu vetores por default, importou após forget e
repetiu com `imported=0`. O processo encerrou engine/pool no lifecycle do
servidor.

A pendência documental histórica foi resolvida com a publicação de
`R09-contract-ready.md`. Não há blocker de execução dentro da Lane B; os
próximos gates pertencem às Fases Q/A.
