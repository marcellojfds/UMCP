---
title: 04 — Fechar multi-tenancy, criptografia e recuperação
status: ready-after-03
order: 4
owner: Terra high
depends_on: 03-AUTH-CONSENT-REVOCATION.md
unlocks: 05-REAL-CLIENT-CONNECTORS.md
---

# 04 — Fechar multi-tenancy, criptografia e recuperação

## Resultado esperado

Toda query, mutação, export, worker e restore opera com tenant context
fail-closed. RLS, constraints, chaves e tombstones formam defesa em profundidade;
um tenant adversarial recebe zero dados e uma memória esquecida não reaparece
após restore.

## Escopo

- tabelas de identity/tenant/membership/connection/consent/audit/tombstone;
- `tenant_id` em todo aggregate e FK/índice composto relevante;
- FORCE RLS default-deny e roles separadas;
- envelope encryption server-decryptable por tenant;
- key version, rotation, rewrap e revocation;
- jobs assinados tenant-bound com replay protection;
- backup, restore isolado e reaplicação de tombstones;
- export/delete concorrentes;
- observabilidade redigida.

Não alegar E2EE, zero knowledge ou operator inaccessibility.

## Tarefas executáveis

1. Congelar migration plan aditivo e rollback por forward-fix/restore.
2. Adicionar tenant context obrigatório à Unit of Work.
3. Criar constraints compostas e FORCE RLS.
4. Separar roles de migration e aplicação.
5. Implementar encryption envelope sem fallback plaintext.
6. Versionar key IDs e cobrir rotation/rewrap.
7. Classificar embeddings como sensíveis e protegê-los com RLS/storage controls.
8. Implementar tombstones duráveis antes de deletion async.
9. Assinar jobs e validar expiry/nonce/dedupe/tenant.
10. Criar matriz adversarial por operação e job.
11. Criar restore drill em alvo isolado.
12. Atualizar threat model e claims permitidas/proibidas.

## Acceptance test

- tenant A nunca lê, altera, relaciona, exporta ou esquece dado de B;
- query sem tenant context falha;
- worker sem envelope válido entra em failed/DLQ sem executar;
- troca de ciphertext/tenant falha autenticação criptográfica;
- falha de key service não usa plaintext;
- rotation preserva leitura conforme política;
- export/forget concorrente é consistente;
- delete durante re-embedding não ressuscita vetor;
- backup→restore→tombstones mantém forget;
- audit não contém payload.

## Comandos de aceitação

```bash
./scripts/gate-postgres
python -m pytest -q tests/security tests/integration tests/workers
python -m pytest -q tests/operations -k 'backup or restore or tombstone or rotation'
./scripts/demo-backup-delete-restore
./scripts/scan-runtime-output
```

## Gate de saída

- cross-tenant leakage zero em toda matriz;
- restore/deletion/rotation demonstrados;
- RLS e application authorization revisados independentemente;
- claims criptográficas literais e limitadas à evidência;
- nenhum downgrade destrutivo;
- handoff inclui migrations, forward-fix e operação de emergência.

## Rollback

- bloquear tráfego e restaurar em isolamento;
- reaplicar tombstones antes da reabertura;
- forward-fix para migrations já aplicadas;
- revogar key/credential afetada conforme runbook;
- desabilitar workers sem permitir execução sem tenant.

## Prompt de execução

```text
Execute docs/execution/mcp-readiness/04-MULTITENANCY-SECURITY.md em worktree
Terra exclusiva. Use banco e dados descartáveis nos testes. Não faça downgrade
destrutivo, não use fallback plaintext e não alegue E2EE/zero knowledge.
Infraestrutura hospedada é dependência de outra lane. Feche todas as operações
e jobs com tenant context, execute restore/delete/rotation, obtenha revisão
independente e produza handoff/commit local.
```
