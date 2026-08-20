# S05 — Privacy/Ops gate

**Executado em:** 2026-08-20
**Decisão para o RC local/self-hosted:** **GO condicional**

O gate vale somente para o Alpha local com PostgreSQL 16 + pgvector. Não
autoriza hosted, auth multi-tenant, E2EE, criptografia custom ou qualquer claim
de zero knowledge. A decisão permanece condicionada aos jobs obrigatórios de CI
estarem verdes no commit que formar o RC.

## Matriz de claims de `docs/privacy.md`

| Claim | Evidência executável ou limitação explícita |
|---|---|
| PostgreSQL local suportado | `./scripts/gate-postgres`: PostgreSQL 16.15, pgvector 0.8.6, Alembic zero→head, integration/E2E. |
| Separação lógica por owner | `tests/integration/test_postgres_retrieval.py` cobre search/update/relation/forget cross-owner; `tests/e2e/test_mvp0_journey.py` cobre o fluxo pelo servidor oficial. Limitação: `owner_id` é confiável apenas no modo local. |
| Logs sem conteúdo por default | `tests/contract/test_privacy_operations.py::test_canary_secret_and_pii_do_not_reach_logs_traces_or_errors` e `scripts/scan-runtime-output`. Não há exporter de tracing no Alpha; o trace-capture de teste contém somente campos allowlisted. |
| Forget online remove dados | integração verifica cascade de memória, versões, embeddings e relações; E2E repete forget idempotente. |
| Export padrão sem embeddings | integration/E2E e `tests/contract/test_export_import.py`; `includes_embeddings=false` e não há `embedding_values`. |
| Erros públicos não expõem SQL/stack/payload | contrato injeta `RuntimeError` com SQL/canário e exige `internal_error` opaco. |
| Secrets/config não aparecem em status | `OMPSettings.safe_summary` omite URL/SecretStr; health/readiness retornam somente status. |
| Demo não é fallback | `test_readiness_fails_closed_and_default_runtime_never_selects_demo`; o processo padrão falha se readiness Postgres falhar. Demo requer flag explícita. |
| Timeout não gera retry storm | `test_timeout_is_single_attempt_without_retry_storm`: uma chamada, `dependency_unavailable`, sem retry interno. |
| Backup/restore/forget após restore | `scripts/backup-postgres`, `scripts/restore-postgres` e `docs/runbooks/mcp-local.md`; cenário sintético executado em Postgres 16 descartável: backup, forget, restore e busca restaurada. Reaplicação de forget é procedimento obrigatório. |
| Retenção/deleção | runbook fixa que logs/backups/exports são do operador, que CI não envia esses dados e que restore só volta a uso após reaplicar deleções. |

## Controles verificados

- Scanner fail-closed para canário de conteúdo/PII sintético e padrões de
  segredo em stderr, trace-capture e diretórios de saída: `scripts/scan-runtime-output`.
- Workflow `security-artifacts` executa os contratos de canário; `package`
  rejeita paths/segredos em wheel/sdist antes do único upload, retido por 1 dia.
- `/healthz` continua vivo sem banco; `/readyz` retorna somente `503
  {"status":"not_ready"}` quando a dependência falha.
- SIGTERM no processo stdio foi exercitado sem fallback para demo; o runtime
  fecha o engine no bloco `finally`.
- `./scripts/gate-postgres` passou no ambiente descartável com migrations,
  integration e E2E (PostgreSQL 16.15 + pgvector 0.8.6).

## Backup e incidente

O procedimento reproduzível está em `docs/runbooks/mcp-local.md`:

```bash
OMP_DATABASE_URL='postgresql://...' ./scripts/backup-postgres /secure/omp.dump
OMP_DATABASE_URL='postgresql://.../omp_restore_gate' ./scripts/restore-postgres /secure/omp.dump
```

Use cliente PostgreSQL da mesma major ou mais novo que o servidor. Neste
executor, `pg_dump` local era v14 e recusou corretamente o servidor v16; a
validação sintética usou `pg_dump`/`pg_restore` v16 dentro do container
descartável. Isso é requisito operacional, não fallback do produto.

## Riscos aceitos / limitações

- Operador, processo, dump, backup e export leem conteúdo e embeddings em
  plaintext.
- `owner_id` é spoofable fora da premissa local confiável; não há auth hosted.
- Embeddings são sensíveis e não anônimos.
- Forget não revoga exports, backups externos ou logs de coletores mal
  configurados. Não existe apagamento imediato de cópias externas.
- Não há exporter de tracing no Alpha; se um for adicionado, ele deve passar o
  scanner/contrato de canário antes de habilitação.
- Não há fila externa de tombstones: o operador conserva e reaplica a lista de
  deleções após restore, sem guardar conteúdo no ledger.

## Blockers para escopo maior / ações restantes

- **Bloqueador hosted:** identity/authz real antes de aceitar tenants não
  confiáveis.
- **Bloqueador de claim forte de deleção:** tombstones externos e política de
  retenção executada pelo storage do operador; não alegar apagamento imediato.
- **RC geral:** CI obrigatório deve executar verde no commit candidato; S06/S07
  ainda devem fechar security reporting, governança e auditoria de release.

## Comandos reproduzíveis

```bash
bash -n scripts/scan-runtime-output scripts/backup-postgres scripts/restore-postgres
ruff check tests/contract/test_privacy_operations.py
mypy src
pytest -q tests/unit
pytest -q tests/contract/test_privacy_operations.py
pytest -q tests/contract/test_mcp_contract.py -k 'canary or timeout or health or official'
./scripts/gate-postgres
./scripts/scan-ci-safety
```

`scan-ci-safety` exige um worktree com arquivos já versionados e, portanto,
falha de modo esperado antes do primeiro commit. Nenhum commit, push, artifact
externo ou mudança de branch protection foi feito nesta sessão.
