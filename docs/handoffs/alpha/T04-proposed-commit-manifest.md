# T04 — Manifesto de commits propostos (somente revisão)

**Data:** 2026-08-20
**Branch local:** `terra-alpha-recovery`
**Base:** `main` em `4947ebfb3789558892c242e0d7a8743256f3656d`
**Operações remotas / holdout:** não executados

## Escopo e verificações desta revisão

Esta é uma decomposição proposta do diff já existente; não houve `git add`,
commit, push, PR, alteração de GitHub nem execução de holdout. A criação da
branch preservou todas as alterações tracked e untracked preexistentes.

Verificações somente leitura concluídas:

- `git diff --check`: aprovado;
- `./scripts/scan-ci-safety`: aprovado;
- os 14 diretórios de relatórios com `checksums.json` foram verificados, sem
  divergência de hash;
- não há cache, peso de modelo, virtualenv, dump de banco ou arquivo de
  `/private/tmp` no status candidato a commit. Diretórios ignorados
  `__pycache__` podem existir localmente, mas não integram este manifesto e
  devem continuar excluídos.

Os diretórios de relatório abaixo são paths exatos: cada um contém apenas seus
arquivos versionáveis de evidência (`report.json`, `report.md` e
`checksums.json`). Não se usa glob para incluí-los.

## 1. Runtime, storage, migrations, re-embedding e regressões

**Mensagem proposta:** `feat: add offline E5 semantic storage and re-embedding`

**Paths exatos:**

- `migrations/versions/0003_semantic_embedding_profile.py`
- `migrations/versions/0004_semantic_embedding_source_version.py`
- `src/omp/adapters/embeddings/__init__.py`
- `src/omp/adapters/embeddings/hash_provider.py`
- `src/omp/adapters/embeddings/local_transformer_provider.py`
- `src/omp/adapters/postgres/repository.py`
- `src/omp/adapters/postgres/schema.py`
- `src/omp/application/ports.py`
- `src/omp/application/reembedding.py`
- `src/omp/application/services.py`
- `src/omp/config.py`
- `src/omp/migrate.py`
- `src/omp/server/composition.py`
- `tests/contract/test_privacy_operations.py`
- `tests/integration/test_postgres_retrieval.py`
- `tests/unit/test_application.py`
- `tests/unit/test_reembedding.py`

**Justificativa:** introduz o provider local/offline de embeddings semânticos,
o armazenamento paralelo de 384 dimensões, isolamento por profile,
re-embedding/cutover/rollback e a correção mínima de `source_version` para
escritas 384d. A alteração preserva o caminho `hash/v1` de 64d. As regressões
cobrem create, update, import, exclusão de vetor stale e a constraint
`source_version >= 1`.

**Dependências:** nenhuma entre os commits propostos; este é o fundamento para
os commits 2 e 3.

**Testes necessários antes do commit:** `./scripts/gate-fast`; os testes
unitários de application/re-embedding; e, no compose descartável `omp_test`,
as migrations zero → head e o teste de integração PostgreSQL de retrieval.

**Riscos:** migrations aditivas e execução local do provider podem falhar em
ambientes sem as dependências opcionais do modelo. A migration `0004` deve
continuar aplicada somente sobre schema que já tenha `0003`.

**Exclusões confirmadas:** nenhum cache, peso, venv, dump ou artifact de
`/private/tmp` pertence a este conjunto.

## 2. Eval, calibração, configurações, reports e handoffs

**Mensagem proposta:** `eval: preserve E5 calibration and development evidence`

**Paths exatos:**

- `evals/configs/semantic-all-minilm-l6-v2.yaml`
- `evals/configs/semantic-bge-small-en-v1.5.yaml`
- `evals/configs/semantic-e5-small-v2.yaml`
- `evals/configs/semantic-e5-small-v2-promotion.yaml`
- `evals/requirements-semantic-s08.txt`
- `evals/reports/20260820T115601Z-4947ebfb3789-semantic-development/`
- `evals/reports/20260820T190703Z-4947ebfb3789-semantic-development/`
- `evals/reports/20260820T193539Z-4947ebfb3789-semantic-development/`
- `evals/reports/20260820T201046Z-4947ebfb3789-semantic-development/`
- `evals/reports/20260820T201231Z-4947ebfb3789-semantic-development/`
- `evals/reports/20260820T203327Z-4947ebfb3789-semantic-development/`
- `evals/reports/20260820T203526Z-4947ebfb3789-semantic-development/`
- `evals/reports/20260820T203648Z-4947ebfb3789-e5-small-v2-s09-development-postgres/`
- `evals/reports/20260820T204511Z-4947ebfb3789-semantic-development/`
- `evals/reports/20260820T204609Z-4947ebfb3789-e5-small-v2-s09-development/`
- `evals/reports/20260820T204707Z-4947ebfb3789-e5-promotion-development-equivalence/`
- `src/omp/evals/runner.py`
- `src/omp/evals/semantic_harness.py`
- `tests/evals/test_semantic_harness.py`
- `docs/adr/0006-semantic-embedding-selection.md`
- `docs/adr/0008-profile-threshold-calibration.md`
- `docs/handoffs/alpha/S08-R3-BGE-semantic-development.md`
- `docs/handoffs/alpha/S08-semantic-embedding-selection.md`
- `docs/handoffs/alpha/T01-eval-diagnostic.md`
- `docs/handoffs/alpha/T02-e5-promotion-validation.md`
- `docs/handoffs/alpha/T03-e5-development-promotion-eligible.md`

**Justificativa:** preserva integralmente a evidência de BGE e E5, registra a
escolha operacional explícita de E5 (sem alegação de superioridade estatística)
e congela a regra de mediana que fixa threshold `0.76`. Inclui o NO-GO
histórico, o desvio de execução documentado e a nova época development que
atingiu elegibilidade de promoção, com `holdout_executed=false` em todos os
novos artifacts.

**Dependências:** requer o commit 1, pois harness, runner e validação real
usam o provider e o storage semânticos. Deve ser aplicado antes do commit 4,
que o referencia como evidência de governança.

**Testes necessários antes do commit:** `pytest -q tests/evals`; validação
development única, já registrada, nos caminhos harness e
PostgreSQL/repository/application/gateway; e a checagem de equivalência de IDs
e scores (tolerância `1e-6`) a partir dos artifacts checksummed. Não executar
novamente esta época para selecionar threshold ou modelo.

**Riscos:** os relatórios são evidência histórica ligada a uma árvore ainda
não commitada, identificada pelo SHA-base. A leitura do JSONL combinado ainda
ocorre antes do filtro de split; os runners não medem, ranqueiam ou reportam
holdout nesta execução, mas isso não constitui selagem física de holdout.

**Exclusões confirmadas:** os relatórios contêm somente dados sanitizados
(IDs/scores) e checksums; nenhum cache, peso, venv, dump ou artifact de
`/private/tmp` pertence a este conjunto.

## 3. Packaging, supply-chain e documentação pública

**Mensagem proposta:** `build: package semantic runtime and audit inputs`

**Paths exatos:**

- `constraints/py311-macos-arm64.txt`
- `pyproject.toml`
- `scripts/audit-dependencies`
- `scripts/generate-sbom`
- `docs/installation.md`
- `docs/protocol.md`
- `docs/support-matrix.md`

**Justificativa:** declara as dependências opcionais do runtime semântico,
inclui constraints reproduzíveis e adiciona scripts de auditoria/SBOM. A
documentação pública correspondente descreve instalação, protocolo e matriz
de suporte sem declarar release GO.

**Dependências:** requer o commit 1 para que os extras e o entrypoint de
migration descrevam código existente. É independente da decisão de promoção
em development registrada no commit 2.

**Testes necessários antes do commit:** build/instalação em ambiente limpo
para o alvo `py311-macos-arm64`, execução de `scripts/audit-dependencies`,
geração do SBOM e smoke de `omp-migrate` contra banco descartável.

**Riscos:** a constraints é específica de Python 3.11/macOS arm64; qualquer
expansão a outra plataforma exige arquivo e validação próprios. O audit depende
da disponibilidade local das ferramentas declaradas.

**Exclusões confirmadas:** constraints e SBOM tooling não incluem wheel cache,
pesos, venv, dump ou artifact de `/private/tmp`.

## 4. Gameplans, progress e governança

**Mensagem proposta:** `docs: record alpha recovery governance and boundaries`

**Paths exatos:**

- `README.md`
- `docs/GAMEPLAN_LUNA_GOAL_ALPHA.md`
- `docs/GAMEPLAN_TERRA_RECOVERY.md`
- `docs/adr/0007-e5-runtime-and-reembedding.md`
- `docs/handoffs/alpha/GOAL-PROGRESS.md`
- `docs/handoffs/alpha/S09-design-review.md`
- `docs/handoffs/alpha/TERRA-RECOVERY-PROGRESS.md`
- `docs/handoffs/alpha/T04-proposed-commit-manifest.md`
- `docs/known-issues.md`
- `docs/privacy.md`

**Justificativa:** mantém o histórico de decisões e limites de autoridade,
incluindo o recovery Terra, status de progresso, revisão S09, privacidade e
limitações conhecidas. O presente manifesto torna a futura operação de stage
revisável e reproduzível.

**Dependências:** aplicar após os commits 1–3. Não altera seus resultados nem
converte elegibilidade development em GO de release.

**Testes necessários antes do commit:** `git diff --check`,
`./scripts/scan-ci-safety` e revisão de consistência entre ADRs, handoffs,
README e documentação pública. Não requer nem autoriza holdout.

**Riscos:** documentos históricos contêm NO-GO anterior e a elegibilidade
development posterior; devem permanecer juntos para evitar reinterpretação ou
apagamento de evidência. Nenhum texto deve alegar SHA limpo, CI remoto verde,
auditoria independente S07-R2 ou GO de release.

**Exclusões confirmadas:** nenhum cache, peso, venv, dump ou artifact de
`/private/tmp` pertence a este conjunto.

## Próximo limite de autorização

Este manifesto não efetua stage. A próxima ação possível é um `git add`
restrito **somente aos paths do conjunto 1**, seguido de nova inspeção do
staged diff; ela requer autorização explícita separada. Não há autorização
para commit, push, PR, holdout, tag, release, GitHub ou qualquer ação remota.
