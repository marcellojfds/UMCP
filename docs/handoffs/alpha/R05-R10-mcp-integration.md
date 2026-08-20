# Handoff Alpha — R05–R10 MCP/DX

## Resultado

As partes independentes e a composição oficial foram implementadas. O servidor
Alpha usa MCP stdio pelo pacote oficial `mcp`, seleciona PostgreSQL por default,
recusa fallback silencioso e oferece o backend file-backed somente com flag
explícita. R05–R10 não são declarados concluídos: PostgreSQL/pgvector não
estava disponível neste terminal e os ports de export/import ainda não foram
expostos pelo core.

## Arquivos alterados

- `src/omp/server/{composition,official,__init__,__main__}.py`
- `src/omp/config.py`
- `src/omp/adapters/mcp/{adapter,application_gateway,schemas,transport}.py`
- `src/omp/sdk/{__init__,client,local}.py`
- `src/omp/cli/main.py`
- `tests/contract/test_cli.py`, `tests/contract/test_mcp_contract.py`
- `tests/e2e/test_mvp0_journey.py`
- `examples/{e2e_two_clients,mcp_stdio_client}.py`
- `docs/adr/0004-composicao-transporte-mcp-alpha.md`
- `docs/protocol.md`, `docs/runbooks/mcp-local.md`
- `docs/handoffs/alpha/R09-core-request.md`

O handoff histórico `docs/handoffs/mcp-mvp0.md` foi marcado como superseded e
corrigido quanto ao pacote oficial/transport.

## Contrato final

- OMP protocol: `omp.mcp.v0`; MCP SDK handshake: `2025-11-25`.
- Transport suportado: stdio; HTTP somente `/healthz` e `/readyz`.
- Tools: `memory.write`, `memory.search`, `memory.update`, `memory.forget`.
- `min_relevance=0.78`, timeout default 2500 ms, timeout máximo 5000 ms,
  content máximo 16384, query máximo 4096 e limit máximo 50.
- Respostas incluem `protocol_version` e `request_id`; schemas estritos
  rejeitam campos desconhecidos.
- `update` propaga `expected_version` e `idempotency_key`; `forget` propaga
  `idempotency_key` e não ecoa conteúdo. Idempotency conflict interno é
  publicado como `validation_error`, pois os códigos públicos v0 permanecem
  os sete definidos no contrato.
- `reason_retrieved`, `profile_id` e `profile_version` são preservados do core.
- Backend default: `postgres`; migration readiness: `0002_idempotency_operations`.

## Composição e lifecycle

`create_runtime()` compõe `OMPSettings`, `create_postgres_uow_factory()`,
`HashEmbeddingProvider`, `MemoryApplicationService`,
`MemoryApplicationGateway` e `MCPAdapter`. A engine é criada sem conexão em
import, readiness verifica `SELECT 1`, pgvector e migration head, e `close()`
descarta a engine. Falha de readiness encerra o servidor com status 78; não
ativa fake/file.

## Transport/client testados

O caminho oficial foi exercitado localmente com `FastMCP`,
`ClientSession`/`stdio_client`, `initialize`, `tools/list` e as quatro
`tools/call` usando o demo explicitamente solicitado. O handshake observado foi
MCP `2025-11-25`, com schemas root `additionalProperties=false`.

## Comandos e resultados

Comando de smoke oficial executado:

```bash
PYTHONPATH=src python - <<'PY'
from omp.sdk.client import MemoryClient, OfficialStdioTransport
client = MemoryClient(OfficialStdioTransport(demo_backend=True, data_file='/tmp/omp-official.json'))
print(client.capabilities()['tools'])
print(client.write(
    content='Synthetic official MCP smoke memory',
    type='fact',
    owner_id='smoke-owner',
    provenance={'source_type': 'system', 'captured_at': '2026-01-01T00:00:00Z'},
    idempotency_key='official-smoke-write',
)['status'])
print(client.search(query='official MCP smoke', owner_id='smoke-owner')['count'])
PY
```

Resultado: quatro tools descobertas, write criado e search retornou um item no
servidor FastMCP/stdio oficial. O comando equivalente sem `--demo-backend`
retorna `dependency_unavailable`/status não-zero quando o Postgres não está
pronto, sem traceback ou fallback.

`PYTHONPATH=src pytest -q tests/contract tests/e2e` retornou `15 passed, 1
skipped`; o único skip foi o E2E PostgreSQL sem `OMP_TEST_DATABASE_URL`. A
suíte completa local retornou `36 passed, 9 skipped`; os oito skips adicionais
de integração também exigem PostgreSQL/pgvector.

## E2E PostgreSQL

O teste obrigatório está em `tests/e2e/test_mvp0_journey.py`. Ele aplica
migrations, inicia processos reais `python -m omp.server` via
`stdio_client`, reconecta um segundo cliente, verifica busca positiva/zero,
isolamento cross-owner, conflito stale, update/replay/idempotency conflict,
forget, cascade SQL e canary scan de logs. Não importa
`InMemoryMemoryService` nem `PersistentLocalMemoryService`.

Evidência desta sessão: não executado com PostgreSQL; `OMP_TEST_DATABASE_URL`
não foi fornecido e o daemon Docker/`pg_isready` não estava disponível. Sem
essa evidência o Gate B permanece aberto. Use
`OMP_REQUIRE_POSTGRES_TESTS=1 pytest -q tests/e2e` para tornar ausência/falha
um erro explícito.

## Export/import

Não concluído contra PostgreSQL. O core não oferece ainda o port administrativo
necessário; a solicitação precisa ser atendida conforme
`docs/handoffs/alpha/R09-core-request.md`. O CLI não chama o fake/file quando o
backend é Postgres.

## Defaults, limitações e riscos

- `owner_id` no payload é aceitável apenas no modo local; hosted auth não foi
  implementado.
- Demo é explícito e não é evidência de persistência Postgres.
- Não há `memory.related`, writer inteligente, reranking LLM, consolidação,
  UI ou claims de E2EE.
- A busca ainda depende do embedding/retrieval real do core; o E2E deve ser
  executado com pgvector antes do release.
- Migration é comando/runbook separado, nunca automática por processo.

## Próximo consumidor

Lane A/core deve fornecer os ports R09 e garantir que o ambiente de CI ofereça
PostgreSQL + pgvector. A revisão seguinte deve executar o E2E com
`OMP_REQUIRE_POSTGRES_TESTS=1` e confirmar que
`create_postgres_uow_factory()` é exercitado pelo servidor real.
