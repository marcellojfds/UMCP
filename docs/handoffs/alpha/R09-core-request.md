# R09 — solicitação de ports de export/import ao core

## Estado

Bloqueado para a integração Postgres. O SDK/CLI já valida o envelope
`omp.export.v0`, rejeita embeddings por default e suporta `--dry-run`, mas o
transport oficial não deve chamar APIs do fake/file para representar Postgres.

## Contrato mínimo solicitado

Expor no application/core um port administrativo assíncrono, owner-scoped,
sem conteúdo em logs, com operações equivalentes a:

```python
export_memories(*, owner_id: str | None, include_embeddings: bool = False) -> Sequence[MemoryExportRecord]
import_memories(*, records: Sequence[MemoryImportRecord]) -> ImportResult
```

Requisitos do port:

- export transacional e consistente; embeddings não são retornadas quando
  `include_embeddings=False`;
- import valida todos os records, IDs, enums, timestamps, versões, owners e
  provenance antes de mutar;
- import executa em uma transação e faz replay idempotente sem duplicação;
- payload divergente para o mesmo ID/identidade retorna erro interno mapeável,
  sem SQL ou conteúdo na mensagem;
- o port deve preservar os campos necessários para round-trip sem depender de
  `export_records`/`import_records` de `PersistentLocalMemoryService`;
- o port deve documentar a política para embeddings, versões históricas,
  relações e o ledger de idempotência.

## Consumidor

Lane B implementará o adapter SDK/CLI assim que as interfaces reais aparecerem.
Até lá, `omp export`/`omp import` em backend Postgres retornam
`dependency_unavailable`; `import --dry-run` ainda pode validar um arquivo sem
mutação quando o processo chega ao arquivo.
