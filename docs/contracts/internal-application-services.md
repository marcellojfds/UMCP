# Contrato interno — application services v0

O objeto `MemoryApplicationService` é a fachada que MCP, SDK, CLI e HTTP devem
consumir. Seus métodos são async e aceitam dataclasses em
`omp.application.models`:

- `write(WriteMemoryCommand) -> WriteMemoryResult`;
- `search(SearchMemoryCommand) -> SearchMemoryResult`;
- `update(UpdateMemoryCommand) -> Memory`; `UpdateMemoryCommand` accepts an
  optional `idempotency_key` and replays the stored result version without a
  second increment;
- `forget(ForgetMemoryCommand) -> ForgetMemoryResult`;
  `ForgetMemoryCommand` accepts an optional `idempotency_key`; the first effect
  returns `forgotten=true` and all later calls return `forgotten=false`;
- `relate(RelateMemoriesCommand) -> RelateMemoriesResult`.
- `export_memories(owner_id, include_embeddings=False) ->
  tuple[MemoryExportRecord, ...]`;
- `import_memories(owner_id, records) -> ImportResult`.

Erros são subclasses de `OMPError` e possuem `code` estável: `validation_error`,
`not_found`, `version_conflict`, `idempotency_conflict`,
`embedding_profile_mismatch`, `invalid_state_transition`,
`owner_access_denied`, `relation_conflict`, `idempotency_in_progress` e
`import_conflict`, `storage_error`.

`idempotency_conflict` is returned when an operation key is reused with a
different canonical fingerprint. Update fingerprints include the target,
expected version, patch, provenance and lifecycle relation fields; forget
fingerprints include the owner and target only. The idempotency ledger stores
only a digest and result pointer, never content/query/provenance/embedding.

Administrative export/import is owner-scoped and transport-neutral. Export
includes current memory, complete history and owner-scoped relations; vectors
are opt-in. Import validates every record and relation endpoint before the
repository mutates inside the same Unit of Work. Missing vectors are
recomputed only when the configured embedding profile matches the descriptor.
Repeated identical imports return `ImportResult.replayed` without new rows;
divergent payloads return `import_conflict`. Operation-ledger rows are never
exported or imported.

O service não conhece MCP/FastAPI/SQLAlchemy. Um adapter deve converter erros
sem incluir conteúdo, query, owner bruto, provenance sensível ou vetor no
payload de erro/log.
