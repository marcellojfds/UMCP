# Handoff — core MVP 0

## Frente e fase

W01/W02/W03/W06 — fundação, domínio, storage e retrieval baseline do MVP 0.

## Resultado entregue

O pacote Python instalável agora fornece:

- arquitetura `domain -> application <- adapters`, sem imports de framework no
  domínio;
- configuração `OMP_*` tipada com `SecretStr` e `safe_summary()` sem secrets;
- aggregate `Memory`, enums de type/state/relation, provenance, snapshots,
  versionamento e state machine explícita;
- casos de uso async para write, search, update, relate e forget;
- `expected_version`/optimistic concurrency e idempotency key isolada por
  owner, com replay estável e conflito para payload diferente;
- ports explícitos para repository, unit of work, embedding provider e clock;
- fake oficial in-memory para testes de application/MCP sem rede;
- adapter PostgreSQL + pgvector com filtros obrigatórios por owner/profile,
  snapshots, relações e forget transacional/idempotente;
- Alembic migration inicial reproduzível, com extensão pgvector, constraints,
  índices de lifecycle/ownership e IVFFlat cosine baseline;
- embedding adapter `hash/v1`, dimensão 64, determinístico e offline;
- retrieval baseline com states ativos por default, threshold conservador,
  score determinístico, tie-break e `reason_retrieved` sem conteúdo extra;
- fixtures sintéticas canônicas, testes de domínio, isolamento,
  concorrência, idempotência, update conflitante, relações, forget repetido,
  abstention negativa e arquitetura de imports.

## Arquivos criados/alterados neste terminal

- `pyproject.toml`, `README.md`, `alembic.ini`;
- `src/omp/__init__.py`, `src/omp/config.py`;
- `src/omp/domain/{__init__,errors,memory,serialization,types}.py`;
- `src/omp/application/{__init__,fakes,models,ports,services}.py`;
- `src/omp/adapters/embeddings/{__init__,hash_provider}.py`;
- `src/omp/adapters/postgres/{__init__,repository,schema}.py`;
- `migrations/env.py` e `migrations/versions/0001_mvp0_initial.py`;
- `docs/memory-model.md`;
- `docs/contracts/internal-application-services.md`;
- `docs/contracts/internal-repository.md`;
- `docs/adr/0001-mvp0-arquitetura-e-tooling.md`;
- `docs/adr/0002-versionamento-forget-e-profile.md`;
- `tests/__init__.py`, `tests/fixtures/*`, `tests/unit/*` e
  `tests/integration/*` do core.

Arquivos de `src/omp/adapters/mcp`, `src/omp/sdk`, `src/omp/cli`,
`src/omp/server`, `tests/contract` e `tests/e2e` foram criados/editados pelo
outro terminal e não foram alterados aqui. O gateway existente foi somente
inspecionado e exercitado contra os contratos do core.

## Contratos disponibilizados ao terminal MCP

O consumidor deve importar `MemoryApplicationService` e os commands/results de
`omp.application`, ou usar o gateway já presente em
`omp.adapters.mcp.application_gateway`:

- `WriteMemoryCommand`/`WriteMemoryResult`;
- `SearchMemoryCommand`/`SearchMemoryResult` e `SearchFilters`;
- `UpdateMemoryCommand`;
- `ForgetMemoryCommand`/`ForgetMemoryResult`;
- `RelateMemoriesCommand`/`RelateMemoriesResult`;
- ports `MemoryRepository`, `UnitOfWork`, `UnitOfWorkFactory` e
  `EmbeddingProvider`.

Erros internos estáveis estão em `omp.domain.errors`; adapters devem mapear o
campo `OMPError.code` sem expor mensagem sensível. O repository exige
`owner_id` em todas as operações de leitura/escrita/relação. A migration fixa o
profile operacional `hash/v1`, cosine, dimensão 64; profiles incompatíveis não
entram na mesma busca.

## Comandos e resultados

Instalação:

```text
python -m pip install -e '.[dev]'       PASSOU (com acesso de rede aprovado)
```

Qualidade do core:

```text
ruff check src/omp/domain src/omp/application src/omp/adapters/postgres src/omp/adapters/embeddings tests/unit tests/integration migrations
PASSOU — All checks passed

python -m mypy src/omp/domain src/omp/application src/omp/adapters/postgres src/omp/adapters/embeddings
PASSOU — Success: no issues found in 15 source files

pytest -q
PASSOU — 30 passed, 1 skipped
```

O skip é o teste real PostgreSQL/pgvector sem `OMP_TEST_DATABASE_URL`. O
gateway MCP existente foi exercitado com o core e retornou `write=created` e
`search=count 1`.

Migration:

```text
python -m alembic upgrade head --sql > /tmp/omp-migration.sql
PASSOU — SQL contém extension vector, quatro tabelas, constraints e índices

python -m alembic current
PENDENTE — falhou ao conectar no default localhost; não há PostgreSQL rodando
```

O comando exato para validar em banco descartável é:

```text
OMP_DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST:PORT/DB \
OMP_TEST_DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST:PORT/DB \
python -m alembic upgrade head && pytest -q tests/integration
```

Também foi verificado `docker info`: o cliente existe, mas o daemon está
indisponível. `pg_isready -h 127.0.0.1 -p 5432` retornou `no response`.

## Decisões/ADRs

- ADR 0001 fecha Python 3.11+, Hatchling, SQLAlchemy Core async/asyncpg,
  Alembic, Pydantic Settings, Ruff/mypy/pytest e dependências previstas de
  FastAPI, SDK MCP oficial e Typer.
- ADR 0002 fecha snapshots por versão, compare-and-swap, sem state persisted
  `forgotten`, cascade transacional, idempotência por owner e profile
  `hash/v1`/64/cosine.
- Retrieval privilegia precision/abstention: similarity abaixo do threshold
  nunca é resgatada por importance/confidence.
- O alpha local não faz claim de E2EE; conteúdo, provenance e embeddings são
  dados sensíveis legíveis pelo operador da instância.

## Limitações

- Integração contra PostgreSQL/pgvector real e migration do zero não puderam
  ser executadas neste ambiente por ausência de daemon/servidor. A migration
  offline e os testes estão preparados.
- O embedding `hash/v1` é apenas baseline offline; não representa qualidade
  semântica de um modelo de produção e requer re-embedding para troca de
  profile.
- Não há RLS/auth hosted, criptografia client-side, export de embeddings ou
  backups/deletion ledger neste incremento.
- O score não é probabilidade e não é comparável entre embedding profiles.
- O typecheck global ainda reporta erros em arquivos do terminal MCP/SDK/server
  (`src/omp/adapters/mcp`, `src/omp/sdk`, `src/omp/server`); o typecheck do core
  acima está verde e esses arquivos não foram alterados por este terminal.
- `ruff check .` também não está verde por diagnósticos preexistentes/concorrentes
  em MCP, SDK, server, examples e contract/E2E; o comando de lint do core acima
  está verde e nenhum arquivo fora do ownership foi reformato para mascará-los.

## Riscos residuais

- A dimensão 64 e IVFFlat `lists=10` precisam de benchmark com corpus alvo antes
  de qualquer claim de performance.
- Embeddings podem vazar semântica; nenhuma garantia de privacidade forte deve
  ser publicada.
- A configuração default assume um PostgreSQL acessível e a extensão pgvector
  instalada; a operação deve fornecer secrets por ambiente.
- O adapter MCP deve manter defaults conservadores e mapear os scores/profile
  do core sem reintroduzir conteúdo em logs.

## Itens explicitamente não feitos

- MCP protocol/server, SDK, CLI e E2E (ownership do outro terminal);
- writer inteligente, dedupe/contradição assistidos, query expansion, LLM
  reranking, related público avançado e consolidação;
- graph database, UI, hosting, auth, multi-tenant hosted, RLS e E2EE;
- benchmark/eval Gate B completo e teste de PostgreSQL real, bloqueados pelo
  ambiente externo ausente.

## Próxima frente consumidora

O terminal MCP deve conectar seu gateway ao `MemoryApplicationService` usando os
commands acima, preservar o mapeamento de `OMPError.code` e executar novamente
contract/E2E com um UoW in-memory. Quando PostgreSQL/pgvector estiver disponível,
rodar migration do zero, suíte de integração, teste cross-owner e o cenário
MBA market-density → GTM com o repository concreto.
