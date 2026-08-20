# R05–R10 MCP integration — Gate B evidence

## Status

**GREEN — R05–R10 executados contra PostgreSQL + pgvector real.**

O transporte MCP oficial, a composição Postgres default, os contratos, o E2E
sem fake e o export/import real passaram. Os ports efetivamente consumidos são
`MemoryApplicationService.export_memories` e `import_memories`; nenhum fake é
selecionado no backend default.

## Handoffs consumidos

- `R01-contract-ready.md` confirma `idempotency_key` em update/forget, ledger
  `0002_idempotency_operations` e replay.
- `R02-R04-postgres-green.md` foi publicado após o primeiro handoff e confirma
  a execução real da Lane A.
- `R09-contract-ready.md` foi publicado após a integração e documenta os mesmos
  ports reais que a Lane B consumiu, sem interface paralela.

Versões observadas: Python 3.11, `mcp 1.29.0`, PostgreSQL 16.15,
`pgvector/pgvector:pg16`.

## Arquivos alterados nesta entrega

- `src/omp/sdk/export.py`, `src/omp/sdk/client.py`
- `src/omp/server/admin.py`, `src/omp/server/__main__.py`
- `tests/e2e/test_mvp0_journey.py`
- `docs/protocol.md`, `docs/runbooks/mcp-local.md`
- `docs/adr/0004-composicao-transporte-mcp-alpha.md`
- este handoff e `LANE-B-GATE-B.md`

Os arquivos de domínio, application, PostgreSQL, migrations, `pyproject.toml`
e testes unit/integration não foram alterados nesta integração.

## Contrato final e compatibilidade

O Alpha expõe somente `memory.write`, `memory.search`, `memory.update` e
`memory.forget` sobre stdio MCP oficial. Requests são estritos, versionados,
com `protocol_version`, `request_id`, `min_relevance=0.78`, limites públicos e
os sete códigos de erro estáveis. Update exige `expected_version`; forget é
idempotente e não ecoa conteúdo; search vazio é sucesso. `reason_retrieved`,
`profile_id` e `profile_version` vêm do core.

Compatibilidade testada: `mcp 1.29.0`, `FastMCP`, `ClientSession` e
`stdio_client`, PostgreSQL 16.15 com `pgvector/pgvector:pg16`. HTTP é somente
health/readiness; Streamable HTTP não é suportado.

## Qualidade Lane B

```text
ruff check src/omp/adapters/mcp src/omp/server src/omp/sdk src/omp/cli \
  src/omp/config.py tests/contract tests/e2e examples
All checks passed

mypy --strict src/omp/adapters/mcp src/omp/server src/omp/sdk src/omp/cli \
  src/omp/config.py examples
Success: no issues found

PYTHONPATH=src pytest -q tests/contract
15 passed, 1 warning
```

Os testes rápidos usam fakes somente em `tests/contract`. O E2E obrigatório
não importa `InMemoryMemoryService` nem `PersistentLocalMemoryService`.

## Ambiente PostgreSQL auditado

O container descartável `omp-gate-b` foi iniciado com
`pgvector/pgvector:pg16`, PostgreSQL 16.15 e porta host `55432`. Migrations
foram aplicadas até `0002_idempotency_operations` e a extensão `vector` foi
confirmada. O PostgreSQL 14 local sem `vector.control` não foi usado como
evidência.

## E2E real e cliente oficial

Comando:

```bash
OMP_REQUIRE_POSTGRES_TESTS=1 \
OMP_TEST_DATABASE_URL='postgresql+asyncpg://omp:omp@127.0.0.1:55432/omp' \
PYTHONPATH=src pytest -q tests/e2e
```

Resultado: `1 passed in 26.62s`, zero skips.

O teste executou `initialize`, `tools/list`, write, novo processo oficial,
search positivo e vazio, isolamento cross-owner, update stale,
update/replay/idempotency conflict, forget idempotente, cascade SQL,
export/import/replay e scan do artifact de logs. O conteúdo-canário não
apareceu nos logs.

## Export/import real

O CLI/SDK chama os ports reais por um comando administrativo do servidor; não
chama `export_records`/`import_records` no backend Postgres.

```text
omp export: count=1, format=omp.export.v0, includes_embeddings=false
omp import --dry-run: count=0, status=validated
omp import: imported=1
replay: imported=0
search após import: count=1
```

O pacote preserva histórico, relações, perfil de embedding, idempotency key e
write fingerprint. Não contém `embedding_values` por default. O import real
valida todos os registros e chama `MemoryApplicationService.import_memories`
em uma operação transacional; replay não duplica.

## Suíte completa

```bash
OMP_REQUIRE_POSTGRES_TESTS=1 \
OMP_TEST_DATABASE_URL='postgresql+asyncpg://omp:omp@127.0.0.1:55432/omp' \
PYTHONPATH=src pytest -q
```

Resultado registrado: `51 passed, 1 warning`, zero skips.

## Riscos e pendências documentais

A pendência histórica de publicação de `R09-contract-ready.md` foi resolvida.
Ela não exigiu mudança do contrato consumido pela Lane B.

O backend demo permanece explícito e não é evidência do Gate B. HTTP continua
restrito a health/readiness e não é anunciado como Streamable HTTP.

Itens não realizados: autenticação hosted, UI, E2EE, `memory.related`, writer
inteligente, reranking por LLM, consolidação e export de vetores por default.
Não há blocker operacional restante dentro de R05–R10. Os bloqueios seguintes
pertencem às Fases Q/A: evals, CI, privacy/ops, governança e release engineering.

## Próximo consumidor

Consumir `EXECUTION_PLAN_QA_RELEASE.md` e iniciar S00/S01. A execução Lane B
permanece verde e não possui blocker operacional conhecido.
