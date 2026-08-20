# ADR 0002 — Versionamento, forget e embedding profile no MVP 0

## Status

Aceito para o MVP 0.

## Decisão

- A memória corrente mantém `version` monotônica começando em 1.
- Cada versão persistida é um snapshot em `memory_versions`; o snapshot da
  versão corrente é gravado no write/update. O histórico é apagado junto com o
  agregado no forget.
- Update exige `expected_version`. O repository faz o compare-and-swap dentro
  da transação e retorna `version_conflict` sem sobrescrever dados concorrentes.
- `forgotten` não é state persistido. Forget faz delete transacional de
  `memories`, snapshots, embedding e relações incidentes; repetir a operação
  retorna `forgotten=false`.
- Idempotency keys têm unicidade composta `(owner_id, idempotency_key)` e são
  removidas com o agregado. Reuso pelo mesmo owner com payload diferente falha;
  owners diferentes permanecem independentes.
- O MVP usa `hash/v1`, cosine, dimensão 64. O descriptor de cada memória e o
  filtro do repository impedem misturar profiles; trocar profile requer
  re-embedding explícito.
- O vector index usa IVFFlat com `lists=10` na migration inicial. O parâmetro é
  baseline operacional, não um SLO, e deve ser medido com corpus realista.

## Consequências

Forget online é imediato no banco primário, mas backups e retenção operacional
ficam fora deste adapter e devem seguir a política de W07/W11. O alpha local
não promete E2EE; conteúdo e embeddings são legíveis pelo operador da instância.
