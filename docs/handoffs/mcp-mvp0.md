# Handoff — MCP/SDK/CLI MVP 0 (superseded by Alpha R05–R10)

> Historical snapshot. The supported Alpha composition is documented in
> `docs/handoffs/alpha/R05-R10-mcp-integration.md`, `docs/protocol.md` and
> ADR 0004. The package `mcp` is installed and the public transport is stdio.

Frente e fase: W04 + W09 + W11, MVP 0 / Gate B (superfície interoperável e jornada local).

## Resultado entregue

Foi implementada uma superfície MCP v0 executável com:

- `memory.write`, `memory.search`, `memory.update` e `memory.forget`;
- schemas Pydantic estritos e snapshot JSON machine-readable versionado;
- envelopes com `protocol_version` e `request_id`;
- discovery via MCP `initialize`/`tools/list` e `omp/capabilities`;
- MCP stdio via SDK oficial; HTTP opcional somente para health/readiness;
- validação anterior ao application service, limites, timeout, cancellation e rate limiting opcional;
- erros públicos estáveis e mensagens opacas;
- isolamento por owner no boundary e aceitação de `owner_id` somente em `local_mode`;
- mapping para o `MemoryApplicationService` real que surgiu no workspace;
- SDK Python fino, CLI com output humano/`--json`, export/import validado e dry-run;
- health/readiness e logs estruturados por allowlist sem conteúdo, query ou IDs brutos;
- jornada E2E de dois clientes com reconnect/restart, abstention, conflict, update e forget.

## Arquivos criados/alterados sob este ownership

- `src/omp/adapters/mcp/{schemas,errors,adapter,application_gateway,transport,observability,fakes,local}.py`
- `src/omp/adapters/mcp/__init__.py`
- `src/omp/server/{__init__,__main__}.py`
- `src/omp/sdk/{client,export,local,__init__}.py`
- `src/omp/cli/{main,__main__,__init__}.py`
- `docs/protocol.md`
- `docs/contracts/mcp/v0/{README,tools,requests,capabilities}.json`
- `docs/runbooks/mcp-local.md`
- `examples/{e2e_two_clients,mcp_stdio_client}.py`
- `tests/contract/**`
- `tests/e2e/test_mvp0_journey.py`

Não foram alterados `pyproject.toml`, domínio, application, Postgres,
embeddings, migrations, `manifest.md`, `project-context.md` ou
`docs/workstreams/**`.

## Contrato MCP final

- Versão pública: `omp.mcp.v0`.
- MCP handshake no caminho oficial: `2025-11-25`.
- Tools: somente as quatro tools MVP 0; `memory.related` não é exposta.
- `memory.search` tem `limit <= 50`, query <= 4096 bytes/caracteres de input,
  timeout <= 5000 ms e default conservador `min_relevance=0.78`.
- Conteúdo tem limite 16384; scores estão em `[0,1]`.
- `memory.update` exige `expected_version` e patch não vazio.
- `memory.forget` retorna somente `forgotten|already_absent`.
- Códigos públicos: `validation_error`, `not_found`, `version_conflict`,
  `forbidden`, `rate_limited`, `dependency_unavailable`, `internal_error`.
- `reason_retrieved` é fornecido pelo core; o boundary não fabrica chain-of-thought.

## Comandos e resultados

```text
PYTHONPATH=src pytest -q
30 passed, 1 skipped

PYTHONPATH=src pytest -q tests/contract tests/e2e
15 passed

PYTHONPATH=src python examples/e2e_two_clients.py
positive_count=1, negative_count=0, conflict=version_conflict,
updated_version=2, forget=forgotten, after_forget_count=0

PYTHONPATH=src python -m omp.cli eval smoke --json --data-file /tmp/omp-cli-smoke.json
{"positive_count":1,"negative_count":0,"conflict":"version_conflict",
 "updated_version":2,"forget":"forgotten","after_forget_count":0}

ruff check --select F src/omp/adapters/mcp src/omp/sdk src/omp/cli src/omp/server tests/contract tests/e2e examples
All checks passed
```

O skip é `tests/integration/test_postgres_retrieval.py`, que exige
`OMP_TEST_DATABASE_URL`; nenhum banco de teste foi disponibilizado neste
terminal. A suíte de contrato/E2E não depende de rede ou credenciais.

## Compatibilidade e transports testados

- In-process SDK ↔ adapter: testado.
- stdio JSON-RPC com `initialize`, `tools/list`, `tools/call` e reconnect:
  testado pelo exemplo E2E e pelo `StdioTransport`.
- O antigo `POST /mcp` não é um transporte MCP suportado; HTTP fica em
  health/readiness.
- `/healthz` e `/readyz`: testados.
- Pacote Python oficial `mcp`: instalado (1.29.0 no ambiente Alpha) e usado por
  `FastMCP`, `ClientSession` e `stdio_client`.

## Limitações conhecidas

- `InMemoryMemoryService` e `PersistentLocalMemoryService` são harness local
  substituível, não persistência de produção. A composição já aceita e mapeia o
  `MemoryApplicationService` real; export/import administrativo ainda usa a
  API local do harness porque o core não expõe um port de export/import.
- O protocolo local confia em `owner_id`; hosted auth e claims de E2EE/zero
  knowledge não foram implementados.
- O export v0 exclui embeddings e rejeita `include_embeddings=true`; um formato
  opt-in de embeddings requer decisão de privacidade/versionamento.
- O transporte HTTP é uma factory FastAPI, não um processo cloud/managed;
  deployment, auth e TLS ficam fora do MVP.
- O baseline fake de busca é determinístico para a jornada; qualidade de
  retrieval de produção pertence ao core/retrieval e aos evals W08.
- Não há `memory.related`, writer inteligente, reranking por LLM,
  consolidação, UI ou claims de criptografia forte.

## Blockers resolvidos ou restantes

Resolvidos:

- scaffolding/core inicialmente ausente: adapters foram criados contra fake e
  depois integrados aos contracts reais de domínio/application;
- erro de schema/transport HTTP 422 por annotation local: corrigido e coberto;
- import parcial em conflito: pré-validação tornou aplicação atômica no fake;
- erros do core (`ValidationError`, `NotFoundError`, `VersionConflictError`,
  `OwnerAccessError`) foram mapeados para códigos públicos estáveis.

Restantes:

- o mantenedor precisa conectar o app factory ao wiring de Postgres/embedding
  quando definir o entrypoint oficial no `pyproject.toml`;
- o SDK oficial `mcp` e a versão mínima de runtime/dependências precisam ser
  definidos pelo dono de W01/packaging;
- executar a integração PostgreSQL/pgvector com `OMP_TEST_DATABASE_URL` antes
  do Gate B final.

Não foram criados `docs/handoffs/core-contract-change.md` ou
`docs/handoffs/core-mvp0.md` neste checkout; eles não estavam presentes quando
o adapter foi integrado.

## Itens explicitamente não realizados

- não alterei `pyproject.toml`;
- não implementei auth hosted, E2EE, client-side crypto ou claims de zero
  knowledge;
- não implementei `memory.related`, writer, reranker, consolidator ou UI;
- não inicializei Git, não fiz commit, push ou publicação remota;
- não rodei migration/backup de PostgreSQL porque esse ownership e a
  dependência operacional não estavam disponíveis.

Próximos consumidores: W03/W06 para wiring real e retrieval; W11 para o
entrypoint operacional definitivo; W08 para ampliar dataset e medir baseline;
W12 para quickstart/release.
