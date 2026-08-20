# Handoff Alpha — Lane A Gate B fechado

## WP, frente e gate

Lane A — Core/Postgres; Gate B no escopo exclusivo do core, incluindo R02–R04
e o contrato administrativo R09.

## Resultado entregue

O lado Core/Postgres está verde contra PostgreSQL 16 + pgvector real. O banco
descartável foi reproduzido por `./scripts/gate-postgres`, as migrations
chegaram a `0002_idempotency_operations`, a suíte de integração passou sem
skips e os ports de export/import estão prontos para a Lane MCP.

## Arquivos alterados/criados nesta rodada

- `ops/postgres/{compose.yaml,README.md}` — imagem digest-pinned, healthcheck,
  tmpfs e loopback isolado;
- `scripts/gate-postgres` — startup, versão, migration zero/head, integration,
  downgrade/upgrade e cleanup;
- `src/omp/application/{models,ports,services,fakes,__init__}.py` — DTOs,
  `MemoryAdminRepository`, export/import e fake transacional;
- `src/omp/domain/{errors,__init__}.py` — `ImportConflictError`;
- `src/omp/adapters/postgres/{repository,__init__}.py` — admin repository
  PostgreSQL transacional;
- `tests/unit/test_application.py` — quatro cenários R09;
- `tests/integration/test_postgres_retrieval.py` — quatro cenários R09 reais;
- `docs/contracts/internal-{application-services,repository}.md`;
- `docs/adr/0005-export-import-postgres-core.md`;
- `docs/handoffs/alpha/R02-R04-postgres-green.md`;
- `docs/handoffs/alpha/R09-contract-ready.md`.

## Contratos disponibilizados à Lane MCP

```python
records = await service.export_memories(
    owner_id="owner-a", include_embeddings=False
)
result = await service.import_memories(
    owner_id="owner-a", records=records
)
```

Os DTOs são `MemoryExportRecord`, `MemoryImportRecord` e `ImportResult`; o
port concreto fica atrás de `UnitOfWork.admin` como `MemoryAdminRepository`.
Erros novos: `import_conflict`; também são preservados
`validation_error`, `not_found` e `embedding_profile_mismatch`. O consumidor
não deve abrir o repository nem assumir formato SQL.

## Evidência reproduzível

Ambiente final observado:

- Docker Engine `27.4.0`, context `desktop-linux`, aarch64;
- `pgvector/pgvector@sha256:ccc6e83d6e35e931dc7c5def2022729d5a6c370318d099181995567ff1fb4d6b`;
- PostgreSQL `16.15`;
- pgvector extension `0.8.6`;
- head `0002_idempotency_operations`;
- integration: `11 passed, 0 skipped`;
- unit: `24 passed`;
- Ruff e mypy strict da Lane A: verdes.

Comando canônico:

```text
./scripts/gate-postgres
```

O script aceita `OMP_TEST_DATABASE_URL` para um banco descartável externo; sem
ela usa o container próprio. Ambos os caminhos exigem PostgreSQL + pgvector,
nunca SQLite ou fallback sem a extensão.

## Decisões e política R09

Export é obrigatório por owner, preserva memória corrente, histórico e
relações, exclui vetores por default e nunca inclui o ledger de update/forget.
Import valida o pacote completo e endpoints antes de qualquer mutação, usa
uma transação, regenera vetores apenas para profile compatível e trata replay
idêntico como no-op. Payload divergente para o mesmo ID falha com
`import_conflict`.

## Riscos ou débitos

- O Gate B global MCP/E2E permanece responsabilidade da Lane B; este handoff
  não declara contract/E2E MCP verdes.
- Export/import carregam dados sensíveis por definição; o consumidor deve
  aplicar permissões e redaction no envelope/arquivo.
- O índice IVFFlat e `hash/v1` continuam baseline, sem claim de escala ou
  qualidade semântica além dos testes determinísticos atuais.

## Itens não realizados

Nenhum arquivo fora da Lane A foi alterado. Não foram implementados MCP,
server, SDK, CLI, schemas públicos ou E2E nesta rodada.

## Próximo consumidor

Lane MCP deve integrar `MemoryApplicationService`, propagar as keys de
update/forget e adaptar seu envelope administrativo aos DTOs R09. O próximo
gate conjunto deve executar a suíte MCP/E2E apontando para o mesmo ambiente
PostgreSQL real, sem substituir o backend por fake/file.
