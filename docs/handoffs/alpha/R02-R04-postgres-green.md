# Handoff Alpha — R02–R04 PostgreSQL green

## WP, frente e gate

Lane A — Core/Postgres; R02 fixture/suíte real, R03 repository/migrations e R04
profile/retrieval/EXPLAIN.

## Resultado entregue

R02–R04 foram executados contra PostgreSQL 16 + pgvector reais, sem skips. O
fixture aceita `OMP_TEST_DATABASE_URL` externo e o harness local usa um
container pinado em tmpfs, loopback `55433`, healthcheck e cleanup automático.
O repository/application service provaram concorrência, idempotência,
owner-isolation, lifecycle, relações, cascade de forget, retrieval pgvector,
profile incompatível, rollback e export/import administrativo.

## Ambiente e versões

- Docker Desktop / Engine `27.4.0`, context `desktop-linux`, aarch64;
- imagem `pgvector/pgvector@sha256:ccc6e83d6e35e931dc7c5def2022729d5a6c370318d099181995567ff1fb4d6b`;
- servidor `PostgreSQL 16.15` (`aarch64-unknown-linux-gnu`);
- extensão `vector 0.8.6`;
- migration head `0002_idempotency_operations`;
- banco `omp_test`, container descartável, data directory tmpfs.

## Arquivos criados/alterados

- `ops/postgres/compose.yaml`
- `ops/postgres/README.md`
- `scripts/gate-postgres`
- `migrations/versions/0002_idempotency_operations.py`
- `src/omp/adapters/postgres/{repository,schema}.py`
- `src/omp/application/{models,ports,services,fakes}.py`
- `tests/integration/test_postgres_retrieval.py`

## Comandos exatos e resultados

```text
python -m pip install -e '.[dev']
PASSOU; dependências já instaladas/build editable concluído.

./scripts/gate-postgres
PASSOU.
Container healthy; PostgreSQL 16.15; pgvector 0.8.6;
upgrade zero -> 0002; downgrade base; upgrade head novamente;
pytest: 11 passed in 4.74s; 0 skipped; head final 0002.

ruff check src/omp/domain src/omp/application src/omp/adapters/postgres \
  src/omp/adapters/embeddings migrations tests/unit tests/integration
PASSOU.

mypy --strict src/omp/domain src/omp/application src/omp/adapters/postgres \
  src/omp/adapters/embeddings
PASSOU — 15 source files.

pytest -q tests/unit
PASSOU — 24 passed.
```

## Cobertura observada no banco real

- write/replay concorrente, conflito de fingerprint e isolamento de owner;
- update replay sem segundo incremento, stale e duas mutações concorrentes;
- owner/space/type/state/profile filters e abstention conservadora;
- histórico, relações e FK composta cross-owner;
- forget repetido e inspeção SQL de memória, versões, embeddings e relações;
- rollback sem ledger incompleto após falha de embedding;
- EXPLAIN do operador pgvector e índice IVFFlat;
- export/import sem embeddings, reimport, conflito, validação prévia,
  embeddings opt-in e profile incompatível.

## Riscos ou débitos

O índice IVFFlat é baseline de MVP e não constitui benchmark de escala. A
imagem é pinada ao digest observado nesta execução; atualização exige nova
evidência. O harness usa credenciais sintéticas apenas dentro do container
descartável e não monta volumes do host.

## Itens explicitamente não feitos

Nenhum código MCP, server, SDK, CLI, contract test ou E2E foi alterado. O
gateway MCP deve consumir os ports R09 e os comandos já publicados.

## Próximo consumidor

Lane MCP: integrar `MemoryApplicationService`, `MemoryAdminRepository` via
service, propagar idempotency keys e usar `scripts/gate-postgres` como
dependência de ambiente para o E2E real.
