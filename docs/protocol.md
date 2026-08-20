# Protocolo MCP v0

## Transporte e handshake

O Alpha v0 suporta somente MCP sobre stdio. O servidor usa o pacote oficial
`mcp` instalado no projeto; clientes usam `ClientSession` e `stdio_client`.
O protocolo MCP negociado pelo SDK instalado é `2025-11-25`. A versão do
contrato OMP é independente e aparece em toda resposta como
`protocol_version: "omp.mcp.v0"`, junto de um `request_id`.

O endpoint HTTP existente, quando habilitado pela aplicação, expõe apenas
`/healthz` e `/readyz`. Não é um endpoint MCP Streamable HTTP suportado.

## Tools

As únicas tools são `memory.write`, `memory.search`, `memory.update` e
`memory.forget`. Os schemas machine-readable em
[`docs/contracts/mcp/v0`](contracts/mcp/v0/) são o snapshot versionado de
[`schemas.py`](../src/omp/adapters/mcp/schemas.py). Todos os objetos rejeitam
campos desconhecidos (`additionalProperties: false`).

Limites públicos: conteúdo 16.384 caracteres, query 4.096, `limit` máximo 50,
timeout máximo 5.000 ms e timeout default 2.500 ms. `min_relevance` default é
0.78. A validação ocorre antes do application service; cancelamento propaga a
cancelled task e timeout vira `dependency_unavailable`.

`owner_id` vindo do payload só é aceito na composição local/stdio sem auth.
Uma composição hosted deve injetar um principal confiável e rejeitar esse
campo no boundary.

## Respostas e erros

Sucesso tem a forma `{protocol_version, request_id, ok: true, data}`. Erros
públicos são estáveis: `validation_error`, `not_found`, `version_conflict`,
`forbidden`, `rate_limited`, `dependency_unavailable` e `internal_error`.
Mensagens são genéricas: não incluem conteúdo, query, SQL, stack trace,
secrets, owner bruto, IDs brutos ou existência cross-owner.

Busca sem resultados é sucesso com `data.count == 0`. `update` exige
`expected_version`. `forget` não retorna a memória apagada e é representado
como `forgotten` ou `already_absent`. `reason_retrieved` é o texto
determinístico fornecido pelo core; o adapter não executa chain-of-thought nem
cria explicações quando o core já fornece uma.

## Descoberta

`initialize`/`tools/list` são os métodos oficiais MCP. A descoberta OMP expõe
`protocol_version`, `request_id`, `mcp_protocol_version`, `transport: "stdio"`,
as quatro tools e os limites. O status do CLI também informa o backend
selecionado (`postgres` por default ou `demo` quando explicitamente pedido),
sem expor a URL de conexão.

## Execução

Postgres exige `OMP_DATABASE_URL`, extensão pgvector e migration head aplicado
(`0002_idempotency_operations` no Alpha atual).
Execute migrations separadamente antes de iniciar o servidor:

```bash
OMP_DATABASE_URL='postgresql+asyncpg://...' alembic upgrade head
OMP_DATABASE_URL='postgresql+asyncpg://...' PYTHONPATH=src python -m omp.server
```

Para um harness local explicitamente rotulado:

```bash
PYTHONPATH=src python -m omp.server --demo-backend --data-file /tmp/omp-demo.json
```

## Export/import

`omp.export.v0` é um documento aberto e versionado. O export é sempre
owner-scoped no backend PostgreSQL e exige `--owner-id`; o conteúdo não inclui
vetores por default. O documento preserva o perfil de embedding, histórico,
relações e fingerprint de escrita necessários para um replay fiel, sem
serializar o vetor. `omp import --dry-run` valida o pacote localmente e não
abre uma transação de mutação. O import efetivo valida todos os registros
antes de chamar `MemoryApplicationService.import_memories`, executa uma única
operação transacional e retorna `imported: 0` para replay idempotente.

```bash
OMP_DATABASE_URL='postgresql+asyncpg://...' PYTHONPATH=src \
  python -m omp.cli --json export /tmp/omp-export.json --owner-id owner-a
PYTHONPATH=src python -m omp.cli --json import --dry-run /tmp/omp-export.json
OMP_DATABASE_URL='postgresql+asyncpg://...' PYTHONPATH=src \
  python -m omp.cli --json import /tmp/omp-export.json
```

Conflito com uma memória existente retorna `version_conflict`; pacote mal
formado ou incompatível retorna `validation_error`. A flag administrativa que
o SDK usa é um caminho local do CLI, não uma quinta tool MCP.
