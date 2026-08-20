# ADR 0004 — Composição e transporte MCP no Alpha v0

Status: aceito para o Alpha v0

## Decisões

- O único transporte MCP público suportado é stdio, implementado pelo SDK
  oficial `mcp` (`FastMCP` no servidor e `ClientSession`/`stdio_client` no
  cliente). O servidor declara as quatro tools MCP v0 e não oferece um
  transporte HTTP MCP.
- O endpoint HTTP existente fica restrito a liveness/readiness (`/healthz` e
  `/readyz`). Ele não é chamado de MCP Streamable HTTP e não entra na matriz
  de compatibilidade MCP.
- PostgreSQL com pgvector é o backend padrão. A fábrica oficial compõe
  `OMPSettings`, `create_postgres_uow_factory()`, `HashEmbeddingProvider`,
  `MemoryApplicationService`, `MemoryApplicationGateway` e `MCPAdapter`.
  Falha de conexão, extensão ou migration head impede o startup; não há
  fallback silencioso.
- O backend file-backed só pode ser selecionado explicitamente com
  `--demo-backend` (e opcionalmente `--data-file`) ou `OMP_BACKEND=demo`. Ele
  é um harness de demonstração/teste, não evidência do Gate B.
- A engine criada pela fábrica é descartada no encerramento do runtime. A
  aplicação não abre conexões em import e migrations são executadas por
  comando/runbook separado.
- Export/import são operações administrativas do SDK/CLI, não tools MCP
  adicionais. No backend PostgreSQL elas atravessam os ports reais
  `export_memories`/`import_memories` do application service; o file-backed
  equivalente só existe no modo demo explícito.
- Readiness verifica conexão, extensão `vector` e o revision head configurado
  (`0002_idempotency_operations`). Respostas de health/readiness não incluem URL,
  secrets, owner, IDs ou conteúdo.

## Matriz de suporte

| Superfície | Alpha v0 | Observação |
|---|---:|---|
| MCP stdio + SDK oficial | suportado | caminho público |
| FastAPI `/healthz`, `/readyz` | suportado | health, não MCP |
| HTTP MCP/Streamable HTTP | não suportado | sem claim de compatibilidade |
| PostgreSQL + pgvector | suportado | backend default e requisito do Gate B |
| File-backed demo | explícito | `--demo-backend`; não é produção |
| In-memory | testes de contrato | não é composição default |
| `omp.export.v0` PostgreSQL | suportado | owner-scoped, sem vetores por default |

## Consequências

O cliente deve tratar indisponibilidade do servidor como
`dependency_unavailable`; o processo do servidor encerra com status não-zero
quando o Postgres não está pronto. Claims antigos de transporte HTTP MCP ou de
ausência do pacote oficial não são válidos para este release e devem ser
removidos das páginas de execução e handoffs.
