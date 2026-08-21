# Terra recovery progress — OMP Alpha

## T0 / T1 start — 2026-08-20

- Base auditada: `4947ebfb3789558892c242e0d7a8743256f3656d` na branch `main`;
  worktree principal permanece sujo e nada foi staged, committed, pushed ou
  alterado remotamente.
- Inventário atual: eval/harness/reports; provider/re-embedding;
  schema/runtime/migrations; packaging/supply-chain; docs/governança. Nenhum
  cache, peso, dump ou artifact de `/private/tmp` aparece no status do Git.
- Evidência externa preservada e checksum de `model.safetensors` BGE confere:
  `3c9f31665447c8911517620762200d2245a2518d6e7208acc78cd9db317e21ad`.
  O worktree S08 e todos os seis diretórios históricos de reports permanecem.
- Gates locais reproduzidos: `./scripts/gate-fast` (47 passed, um warning
  Starlette/httpx existente), `pytest -q tests/evals` (11 passed) e
  `./scripts/scan-ci-safety` (passed). O gate PostgreSQL não foi executado
  neste checkpoint porque a confirmação/autorização separada do compose
  descartável ainda não foi solicitada.
- Achado T1: os runners existentes filtram `development`, mas chamam antes a
  validação estrutural do corpus JSONL combinado. Não houve inferência,
  ranking, métrica, listagem ou seleção de holdout nesta recovery. Isso não é
  um boundary técnico selado e deve constar da auditoria; os novos artifacts
  declaram development-only e não usam resultado de holdout.
- ADR 0008 foi pré-registrado antes de qualquer sweep: cinco folds por episódio
  e grade fixa de thresholds 0.50--0.90 em passos de 0.01. Os gates públicos
  não foram alterados.

## T1 / T2 — 2026-08-20

- O artifact development-only corrigido é
  `evals/reports/20260820T201231Z-4947ebfb3789-semantic-development/`; seu
  `holdout_executed` é `false`. Nenhum modelo foi adquirido e BGE continua fora
  do runtime.
- E5 e BGE são `CALIBRATION_NO-GO` no threshold histórico 0.78, não
  `RANKING_NO-GO`: ambos têm Recall@5 1.00 e passam os gates out-of-fold da
  calibração pré-registrada. O relatório T01 registra métricas, thresholds e
  limitações integralmente.
- A primeira execução recovery `20260820T201046Z-...` foi preservada mas não
  serve para decisão: ela revelou que o harness mantinha ordem cosine enquanto
  o gateway reordena por similarity/importance/confidence. O harness foi
  corrigido e ganhou teste de regressão antes da repetição decisiva.
- Nenhum candidato foi congelado: a ADR pré-registrou threshold por profile,
  mas não uma regra para reduzir thresholds por fold a uma configuração de
  produção nem um desempate entre E5 e BGE. Escolher retroativamente seria
  seleção pós-medida. Híbrido, PostgreSQL/gateway, holdout e operações Git
  externas não foram executados.

## T2 promotion validation — 2026-08-20

- O mantenedor selecionou E5 por risco operacional e congelou o threshold
  `0.76` pela mediana dos cinco folds; a regra e a configuração separada foram
  registradas antes da validação.
- O harness E5 development foi executado com a configuração congelada.
- A primeira execução do harness produziu `20260820T203327Z-...`; antes do
  caminho PostgreSQL, os runners foram alterados somente para emitir a trilha
  ID/score exigida para equivalência e a mesma configuração foi repetida em
  `20260820T203526Z-...`. O desvio do requisito de execução literal única está
  documentado em T02; não houve variação de modelo, revision, threshold,
  corpus, labels ou gates.
- A validação PostgreSQL/gateway no compose descartável PostgreSQL 16.15 falhou
  antes de métricas: `memory_embeddings_semantic.source_version` é obrigatório,
  mas o insert em `PostgresMemoryRepository.create` não o fornece. O artifact
  de NO-GO preserva o erro sanitizado, checksums e `holdout_executed=false`.
- O compose tmpfs foi removido após a falha. Não houve ajuste de threshold,
  promoção BGE, híbrido, aquisição, holdout ou operação Git externa.

## T3 corrected E5 validation — 2026-08-20

- Corrigido o insert 384d para persistir `source_version=memory.version` sem
  alterar o caminho hash/v1 64d ou criar migration. A regressão integrada de
  create, update, import, stale/concurrency, constraint e hash passou após
  migrations zero→head no compose `omp_test` confirmado.
- A época nova autorizada executou uma vez por caminho, no mesmo código e
  configuração congelada: harness e PostgreSQL/gateway passaram todos os gates
  públicos. IDs são idênticos nas 40 queries development; 44 scores tiveram
  delta decimal máximo `0.000001`, dentro da tolerância `1e-6`.
- Artifact de equivalência e T03 registram `development promotion eligible`,
  não GO. Todos os artifacts novos têm checksums e `holdout_executed=false`.
  O compose foi removido; não houve holdout nem operação Git/remote.
