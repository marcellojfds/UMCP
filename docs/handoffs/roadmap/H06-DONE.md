# H06 handoff — tenancy, RLS, KMS e recuperação local fail-closed

## Estado

`DONE — endurecimento local/sintético; hosted bloqueado por CP-1/CP-2/CP-3`.
O pacote parte do SHA canônico solicitado e entrega interfaces, migration,
adapters locais e testes adversariais. Não há claim de staging, Cloud SQL,
KMS real, PITR hosted ou backup remoto.

## Base, commits e paths

- SHA base canônico: `c1b195dc687becc83135a025bef998dd0d6068b7`.
- Commit de implementação: `7eb3348234bfd19da514ea7c1707e2508387457e`.
- Commit documental/checklist: o commit que contém este handoff.
- Paths de implementação:
  - `migrations/versions/0009_h06_security_recovery.py`;
  - `src/omp/adapters/postgres/repository.py`;
  - `src/omp/cloud/__init__.py`, `encrypted_memory.py`, `recovery.py`,
    `security.py`, `tenant.py` e `worker.py`;
  - `tests/unit/test_cloud_security.py`.
- Path documental adicional: somente `docs/roadmap_implementation.md`, na
  checkbox H06.
- Dados de teste: UUIDs, canários sintéticos e ciphertext local; nenhum
  segredo, credencial ou payload real.

## Entrega

- Migration H06 habilita FORCE RLS default-deny no ledger
  `memory_tombstones`, adiciona índices tenant/aggregate e revoga privilégios
  PUBLIC das tabelas tenant-owned. Não cria roles: runtime, migration,
  worker e break-glass continuam contratos de provisionamento dependentes de
  CP-3.
- PostgreSQL valida o owner `cloud:<tenant UUID>:<subject UUID>`, exige que o
  tenant do owner corresponda ao contexto verificado e aplica a mesma defesa
  em query, mutate, relation, re-embedding, export/import e leitura de rows.
- O contexto transaction-local permanece derivado de principal imutável por
  `verified_principal_scope`; `set_tenant_context` rejeita mismatch.
- Envelopes validam versão, nonce/tag e tamanhos; AAD continua vinculando
  tenant, record, campo e key version. KMS ausente/falho, swap e key mismatch
  falham sem fallback plaintext. `HostedKMSUnavailable` é interface explícita
  e inutilizável até uma integração autorizada.
- Worker local mantém tenant + dedupe + nonce replay protection e assina o
  snapshot inteiro para impedir alteração de payload_ref, estado ou tentativa
  durante restart; referências com conteúdo/espaços são rejeitadas.
- Recovery local produz inventário content-free, mede RPO/RTO somente do
  fixture, restaura apenas em alvo `isolated` e reaplica tombstones antes de
  expor records. O adapter hosted de recovery sempre falha fechado.

## Evidência atual

| Gate | Resultado | Evidência |
| --- | --- | --- |
| H06 adversarial security | PASS | `pytest -q tests/unit/test_cloud_security.py tests/unit/test_h04_identity_contracts.py tests/contract/test_h03_streamable_http.py tests/contract/test_hosted_gateway.py` — 26 passed |
| unit suite | PASS | `pytest -q tests/unit` — 55 passed |
| full local unit/contract | PARTIAL | 108 passed; 5 falhas são somente testes que tentam loopback HTTP e recebem `PermissionError`/endpoint indisponível no ambiente |
| lint/format | PASS | `ruff check .`; `git diff --check` |
| syntax | PASS | `python -m py_compile` nos adapters, cloud e migration H06 |
| migration topology | PASS | `python -m alembic heads` — `0009_h06_security_recovery (head)` |
| PostgreSQL zero→head/RLS | environment-blocked | `./scripts/gate-postgres` tentou iniciar o Compose, mas o daemon Docker está inacessível; nenhuma base foi alterada |
| fast gate | BLOCKED by pre-existing typing | os arquivos H06 passam lint/mypy isolado; o gate global mantém erros anteriores em `src/omp/application/services.py` e outros adapters |

## Claims e limitações

Claim permitido: endurecimento local revisável de tenancy/RLS, envelope,
worker e recovery, com fixtures sintéticas e seams fail-closed.

Claims proibidos: KMS/GCP operacional, IAM, Secret Manager, Cloud SQL,
backup/PITR hosted, RPO/RTO de produção, restore staging, provider/IdP,
credenciais, secrets, deploy, staging ou produção. Vetores continuam
queryable sob RLS/storage encryption; não existe claim E2EE/zero-knowledge.

CP-1, CP-2 e CP-3 permanecem fechados. Nenhuma ação externa, provider,
credencial, segredo, mudança de IAM, deploy ou serviço hosted foi executada.

## Checkpoint e rollback

Checkpoint local: implementação em `7eb3348`; documentação/checklist deve ser
confirmada no commit seguinte deste handoff, sempre com worktree limpa. O
gate PostgreSQL permanece pendente até um ambiente local descartável com
Docker disponível; isso não bloqueia a honestidade do pacote local, mas impede
claim de RLS executada contra PostgreSQL nesta sessão.

Rollback é local: reverter o commit de implementação `7eb3348` e o commit
deste handoff/checklist. Não fazer downgrade destrutivo em banco hosted; em
qualquer ambiente futuro usar forward-fix ou restore isolado verificado.

H07 continua bloqueado até H02/H05/H06 e os checkpoints CP-1, CP-2 e CP-3,
com auditoria limpa no mesmo revision/digest.
