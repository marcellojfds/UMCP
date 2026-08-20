# Handoff Alpha — R00–R04 Core/Postgres

## Frente e fase

Lane A — Core/Postgres; R00 ADR de idempotência, R01 contratos/application,
R02 suíte PostgreSQL, R03 migrations/repository e R04 retrieval/qualidade.

## Resultado entregue

R00 e R01 foram implementados e estão prontos para consumo. O core agora tem
ledger metadata-only para update/forget, claims transacionais, replay exato,
conflito por fingerprint, rollback de claim incompleto, isolamento por owner e
foreign keys compostas owner+memory para relações. A suíte real PostgreSQL +
pgvector foi preparada com migration zero → head, concorrência, lifecycle,
retrieval, filtros, histórico, relações, forget cascade e EXPLAIN.

R02–R04 não são declarados concluídos nesta máquina: PostgreSQL 16/pgvector
real não estava disponível para executar a suíte.

## Arquivos criados/alterados

- `docs/adr/0003-idempotencia-operacoes-update-forget.md`
- `docs/contracts/internal-application-services.md`
- `docs/contracts/internal-repository.md`
- `docs/memory-model.md`
- `docs/handoffs/alpha/R01-contract-ready.md`
- `src/omp/domain/{errors,__init__}.py`
- `src/omp/application/{models,ports,services,fakes,__init__}.py`
- `src/omp/adapters/embeddings/*`
- `src/omp/adapters/postgres/{__init__,schema,repository}.py`
- `migrations/versions/0002_idempotency_operations.py`
- `tests/unit/test_application.py`
- `tests/unit/test_import_boundaries.py`
- `tests/integration/test_postgres_retrieval.py`

`pyproject.toml` e `src/omp/config.py` não foram alterados, conforme o
ownership desta rodada.

## Contratos disponibilizados

`UpdateMemoryCommand` e `ForgetMemoryCommand` aceitam
`idempotency_key: str | None`. O port `IdempotencyRepository` expõe:

```python
claim(owner_id, operation_type, idempotency_key, fingerprint) -> IdempotencyClaim
complete(claim, memory_id, result_version, result_status) -> None
```

`operation_type` é `update` ou `forget`; a chave é isolada por owner e tipo.
Erros estáveis incluem `idempotency_conflict` e
`idempotency_in_progress`. Update replaya o snapshot da versão original sem
novo incremento; forget retorna `forgotten=false` após a primeira remoção.
O handoff R01 contém as assinaturas completas e a ação requerida pelo gateway
MCP, que deve propagar as keys.

## Migration revision

Head: `0002_idempotency_operations`.

- cria `idempotency_operations` com PK `(owner_id, operation_type,
  idempotency_key)`, fingerprint SHA-256 e apenas ponteiros de resultado;
- adiciona unique `(owner_id, id)` em `memories`;
- adiciona FKs compostas owner+source/target para bloquear relações
  cross-owner;
- mantém a extensão `vector` e o índice IVFFlat da 0001.

O downgrade remove o ledger e as constraints adicionadas por 0002; a extensão
continua retida conforme 0001.

## Comandos e resultados

```text
python -m pip install -e '.[dev]'
PASSOU com dependências aprovadas/rede disponível (execução final autorizada).

python -m pip install -e . --no-deps
FALHOU no sandbox: download de build dependency hatchling bloqueado por
DNS/rede; a instalação completa acima passou com escalonamento autorizado.

python -m pip install -e . --no-build-isolation --no-deps
FALHOU: hatchling não estava instalado no ambiente isolado.

python -m alembic upgrade head --sql > /tmp/omp-migration-head.sql
PASSOU; SQL contém vector, 0002, ledger e FKs compostas.

ruff check src/omp/domain src/omp/application src/omp/adapters/postgres \
  src/omp/adapters/embeddings migrations tests/unit tests/integration
PASSOU.

mypy --strict src/omp/domain src/omp/application src/omp/adapters/postgres \
  src/omp/adapters/embeddings
PASSOU — 15 source files sem erros.

pytest -q tests/unit
PASSOU — 21 passed.

pytest -q tests/unit tests/integration
PASSOU local permissivo — 21 passed, 8 skipped por ausência de Docker/Postgres.

OMP_REQUIRE_POSTGRES_TESTS=1 pytest -q tests/integration
FALHOU explicitamente no fixture: daemon Docker indisponível (`http+docker`) e
`pg_isready -h 127.0.0.1 -p 5432` retornou `no response`.
```

## Evidência de PostgreSQL real

Não há evidência real nesta sessão. `docker info` encontrou apenas o cliente e
falhou ao consultar o daemon; não existe servidor local em `127.0.0.1:5432`.
Há apenas binários PostgreSQL 14 locais e o arquivo `vector.control` não está
instalado, portanto eles não substituem o requisito PostgreSQL 16 + pgvector.
O fixture tenta `testcontainers.community.postgres.PostgresContainer` com a
imagem `pgvector/pgvector:pg16`, usa `OMP_TEST_DATABASE_URL` quando fornecida,
executa `alembic downgrade base` e `alembic upgrade head`, e falha sem skip
quando `OMP_REQUIRE_POSTGRES_TESTS=1`.

Com um banco descartável disponível, executar exatamente:

```text
OMP_TEST_DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST:PORT/DB \
OMP_REQUIRE_POSTGRES_TESTS=1 pytest -q tests/integration
```

## Evidência de concorrência/idempotência

A suíte unitária real do application service passou com concorrência de write e
update, replay de update sem segundo incremento, conflito de fingerprint,
forget repetido, isolamento de owner/tipo e rollback de claim após falha de
embedding. A evidência equivalente no repository PostgreSQL está codificada
em `tests/integration/test_postgres_retrieval.py`, mas permanece pendente de
execução contra o banco real.

## Decisões/ADRs

ADR 0003 define fingerprint canônico, ledger, retenção metadata-only,
concorrência, replay depois de forget, dados proibidos e migration 0002.
Alternativas rejeitadas incluem payload completo no ledger, reuso da write key,
tombstone com conteúdo, Redis/lock separado e replay sempre da memória atual.

## Riscos ou débitos conhecidos

- R02–R04 aguardam execução com PostgreSQL 16 + pgvector; não há claim de
  migration aplicada, EXPLAIN ou performance real.
- O modo local permissivo mostra 8 skips; o modo gate não faz skip silencioso e
  falha explicitamente quando o banco falta.
- `HashEmbeddingProvider hash/v1` é baseline determinístico, não um modelo
  semântico de produção.
- `OMPSettings.migration_head` em `src/omp/config.py` permaneceu fora deste
  ownership; consumidores devem usar o Alembic head `0002`/configuração de
  release correspondente antes do gate.
- O gateway MCP existente precisa propagar `idempotency_key` em update e
  forget; nenhum arquivo do outro terminal foi alterado.

## Itens explicitamente não feitos

Não foram implementados writer inteligente, reranking LLM, consolidação,
graph DB, UI, hosting, auth/RLS, E2EE, provider externo, nem mudanças em
MCP/server/SDK/CLI/contract/E2E.

## Próxima frente consumidora

O terminal MCP deve consumir `R01-contract-ready.md`, propagar as duas keys e
mapear os erros internos. Em seguida, um ambiente com PostgreSQL 16 + pgvector
deve executar a suíte em modo gate, incluindo migration zero → head,
concorrência PostgreSQL, cascade SQL e retrieval real antes de fechar R02–R04.
