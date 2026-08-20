# Handoff R09 — contrato administrativo Core/Postgres pronto

## Resultado

O core expõe export/import assíncrono owner-scoped através de
`MemoryApplicationService`. A Lane MCP pode consumir o service sem acessar
SQLAlchemy, sessões ou repositories concretos.

## Assinaturas e DTOs

```python
from collections.abc import Sequence

from omp.application import (
    ImportResult,
    MemoryExportRecord,
    MemoryImportRecord,
    MemoryApplicationService,
)

records: tuple[MemoryExportRecord, ...] = await service.export_memories(
    owner_id="owner-a",
    include_embeddings=False,  # secure default
)
result: ImportResult = await service.import_memories(
    owner_id="owner-a",
    records=records,
)
```

`MemoryExportRecord` e `MemoryImportRecord` contêm:

- `memory: Memory` corrente;
- `history: tuple[MemoryVersion, ...]` completo, de versão 1 à corrente;
- `relations: tuple[Relation, ...]` owner-scoped e incidentes à memória;
- `embedding: tuple[float, ...] | None`, ausente por default;
- `write_fingerprint: str | None`, somente digest necessário para preservar
  replay de write idempotency key.

`ImportResult` retorna `imported` e `replayed`. Uma reexecução idêntica não
cria rows e incrementa apenas `replayed`.

## Erros estáveis

- `validation_error`: records inválidos, owners divergentes, IDs duplicados,
  histórico incompleto, fingerprint/vetor inválido;
- `not_found`: endpoint de relação externo ausente para o owner;
- `embedding_profile_mismatch`: vetor ausente e provider incompatível;
- `import_conflict`: mesmo ID com memória, histórico, relação ou fingerprint
  divergente;
- erros de storage seguem os códigos internos existentes.

Mensagens não incluem conteúdo, query, provenance, vetor, SQL ou owner bruto.

## Semântica transacional

O service materializa e valida todos os records antes de chamar
`UnitOfWork.admin.import_memories`. O repository PostgreSQL grava memórias,
embeddings, snapshots e relações na mesma transação; relações entram depois
das memórias. Qualquer erro faz rollback do pacote inteiro. Reimport idêntico
usa IDs estáveis e `ON CONFLICT DO NOTHING`.

## Política

Export é sempre de um owner. Histórico e relações são preservados. Embeddings
são excluídos por default; se excluídos, import regenera com o provider apenas
quando o profile da memória coincide exatamente. Embeddings fornecidos por
opt-in são validados por dimensão e armazenados. O ledger de update/forget não
é exportado nem importado, e não há reativação de operações após restore.

## Evidência

Unit tests cobrem round-trip, owner scope, validação antes de mutação, conflito
estável e profile incompatível. A suíte PostgreSQL real cobre round-trip sem
embeddings, reimport, histórico, relações, conflito/rollback, vetor opt-in e
profile incompatível.

Ambiente real: Docker Engine `27.4.0`, context `desktop-linux`, aarch64;
imagem `pgvector/pgvector@sha256:ccc6e83d6e35e931dc7c5def2022729d5a6c370318d099181995567ff1fb4d6b`;
PostgreSQL `16.15`; pgvector `0.8.6`; head `0002_idempotency_operations`.

Comando executado:

```text
./scripts/gate-postgres
```

Resultado: `11 passed, 0 skipped` em `tests/integration`; `24 passed` em
`tests/unit`; Ruff e mypy strict da Lane A passaram. O script também executou
zero → head, downgrade base e upgrade head no banco tmpfs descartável.

Risco residual: o envelope MCP/arquivo deve tratar export como dado sensível;
este port não implementa redaction nem criptografia e não autoriza export
global.

## Próximo consumidor

A Lane MCP deve converter o envelope `omp.export.v0` para esses DTOs e chamar
somente `MemoryApplicationService.export_memories`/
`import_memories`. Nenhum arquivo MCP, SDK, CLI ou server foi alterado nesta
entrega.
