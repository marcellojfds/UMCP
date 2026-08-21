# S09 design review

**Status:** NOT APPROVED — aguardando uma nova experiência semântica
explicitamente autorizada.

## Evidência revisada

- S08 corrigida aplica `query:`/`passage:` e retorna NO-GO em development.
- Provider offline-only, migration paralela 64d/384d, `source_version`,
  re-embedding resumível e cutover/rollback foram implementados e testados no
  banco descartável.
- PostgreSQL 16.15 + pgvector 0.8.6: 13 testes, zero skips, head
  `0004_semantic_source_version`.

## Pendências que impedem aprovação

- Selecionar um novo candidato em experiência separada, com revisão e hashes
  pinados; não baixar threshold nem reutilizar holdout.
- Reexecutar development pelo gateway real e obter todos os gates verdes.
- Só depois congelar provider/migration/re-embedding e solicitar abertura do
  holdout selado.

Nenhum commit, push, tag, release ou alteração remota foi feito.
