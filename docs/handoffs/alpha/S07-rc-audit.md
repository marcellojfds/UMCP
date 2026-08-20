# S07 — Auditoria independente do release candidate

**Data:** 2026-08-20
**Decisão:** **NO-GO**
**SHA auditado:** `UNBORN` — `main` não possui commit nem `HEAD`. Portanto não
existe um release candidate imutável que possa ser reproduzido, tagueado ou
publicado.

## Escopo e integridade da auditoria

Foram lidos `README.md`, `pyproject.toml`, `docs/DELIVERY_GAMEPLAN.md`,
`docs/EXECUTION_PLAN_QA_RELEASE.md`, `docs/EVALS_PLAN.md`, `docs/privacy.md`,
`docs/threat-model.md` e todos os handoffs S00--S03 disponíveis. Os handoffs
S04, S05 e S06 **não existem** neste checkout; esta ausência é um finding, não
foi suprida por inferência. Não houve correção de código, commit, push, tag ou
publicação durante esta sessão.

`git status --short --branch` retornou `## No commits yet on main` e todos os
paths do projeto como `??`; `git rev-parse HEAD` falhou. Logo o working tree
não está limpo e não há revisão auditável. Os artifacts abaixo são somente
artefatos temporários da auditoria, gerados em `/private/tmp`, e não podem ser
atribuídos a uma revisão Git.

## Resultado dos gates

| Gate/comando | Resultado | Evidência resumida |
|---|---|---|
| Ruff global: `ruff check .` | **FAIL** | 8 violações em `src/omp/evals/__init__.py` e `src/omp/evals/metrics.py` (`I001`, `E501`, `F841`). |
| Mypy: `mypy src` | PASS | `Success: no issues found in 42 source files`. |
| Unit: `pytest -q tests/unit` | PASS | 24 passed. |
| Contract/MCP E2E sem skips | **INCONCLUSIVO** | A execução integral não foi concluída pela sessão; processos de teste stdio concorrentes impediram uma evidência final limpa. Não há aprovação por evidência parcial. |
| PostgreSQL 16 + pgvector | **INCONCLUSIVO** | Docker 27.4.0, PostgreSQL 16.15 e pgvector 0.8.6 foram verificados. `gate-postgres` chegou a `migration_head=0002_idempotency_operations`; a execução completa integration/E2E sem skips não produziu resultado final auditável. Uma tentativa isolada posterior perdeu o container descartável e falhou com `ConnectionRefusedError` em `127.0.0.1:55433`; isso é falha de execução concorrente, não achado de produto. |
| Migration zero -> head | PASS (parcial) | `downgrade base`, `upgrade head`, `alembic current == 0002_idempotency_operations` e extensão `vector` instalada foram observados no gate. O ciclo pós-testes não foi concluído. |
| Eval completo | **FAIL** | Relatórios existentes `evals/reports/*-UNBORN-hash-v1/report.json`: decisão `NO-GO`, `precision_at_5=0.0` vs meta 0.80; slices `positive` e `cross_domain` vermelhos. Abstention 1.0, isolamento 1.0, p95 4.824--9.723 ms. A execução sem banco pelo sandbox falhou corretamente por permissão de conexão; não altera o NO-GO já registrado. |
| Privacy/ops | **FAIL** | `privacy.md` declara backup/restore/delete-retention e política de retenção como bloqueadores; S05 não existe. |
| Wheel + sdist | PASS, não reprodutível | Build isolado Python 3.11 gerou wheel SHA-256 `bb2127cb1fee63ab3563e45101ff71d33cd847e27622ff58c6e58b1c610e2537` e sdist SHA-256 `37bb8f8c84b06a64d024c9f092be765eabf6ce7bc7106717c8151761ee0fe9db`; ambos são de estado `UNBORN`. Não há lock/constraints. |
| Instalação limpa Python 3.11 | PASS | Wheel instalado em venv novo; `pip check`, `import omp` (`0.1.0a1`) e `omp --help` passaram. |
| Quickstart suportado | **INCONCLUSIVO** | Com o wheel no venv e DB descartável: migration, `omp status --json` e operações MCP foram iniciados com backend `postgres`; o comando completo não finalizou com evidência final limpa. Houve `IncompleteFieldDefinitionWarning` do `pydantic-settings`. |
| Conteúdo de artifacts/secrets | PASS com limitação | Wheel/sdist contêm `LICENSE` Apache-2.0 e não contêm padrão de segredo pesquisado. `scan-ci-safety` falhou corretamente, fail-closed, porque não há arquivos Git rastreados. Varredura estática não encontrou segredo com os padrões definidos; dados de eval são sintéticos. |
| Dependências/licenças | **FAIL** | `pip-audit` no venv limpo reportou 13 vulnerabilidades no bootstrap `pip 24.0`/`setuptools 65.5.0`; não encontrou CVE em dependência runtime resolvida, mas não auditou `open-memory-protocol` por não existir no PyPI. Não há lock/constraints nem SBOM/licenças de dependências verificáveis. |
| Links/snippets/claims | **FAIL** | Links locais de README apontam para arquivos presentes, e as limitações de privacy/hosted/E2EE estão coerentes. Porém README e `known-issues.md` admitem S04/S05 ausentes, enquanto relatórios de eval existentes registram explicitamente `NO-GO`; falta documentação/hand-off final que reconcilie a claim matrix, eval e operações com uma revisão Git. |

## Findings

| ID | Severidade | Finding e evidência | Owner |
|---|---|---|---|
| S07-01 | P0 blocker | Não há commit/SHA e o working tree está integralmente não rastreado; não existe RC imutável nem tree limpa. | Mantenedor/release engineering |
| S07-02 | P0 blocker | Gate B de eval falha: `precision@5=0.0`, abaixo de 0.80, em relatórios `UNBORN`; slices positivos e cross-domain falham. | Owner de retrieval/evals |
| S07-03 | P0 blocker | `ruff check .` falha com 8 erros no código de evals. | Owner de qualidade/evals |
| S07-04 | P0 blocker | S05 e evidência de backup/restore/delete-retention/outage não estão disponíveis; `privacy.md` os classifica como bloqueadores para Alpha público. | Owner de operações/privacy |
| S07-05 | P1 | S04--S06 handoffs exigidos pelo plano não existem, apesar de haver reports `UNBORN`; cadeia de evidência e claims não é auditável. | Coordenação/release docs |
| S07-06 | P1 | Não existe lock/constraints; o build resolve faixas de versão e não é reproduzível. | Release engineering |
| S07-07 | P1 | Wheel não contém `alembic.ini`/migrations; o quickstart requer checkout para inicializar banco. Definir e testar o caminho suportado de instalação/distribuição. | Packaging/ops |
| S07-08 | P2 | `pip-audit` encontrou CVEs no `pip`/`setuptools` bootstrap do venv. Atualizar ferramentas no ambiente de build e registrar audit de dependências runtime/SBOM. | Release engineering |
| S07-09 | P2 | Quickstart emite `IncompleteFieldDefinitionWarning` do `pydantic-settings`. | Owner de configuração |

## Known issues e caminho de upgrade

- Não publique `hash/v1` como retrieval aprovado. Abrir sessão separada para
  investigar a recuperação nula; não baixar a meta, não alterar corpus nem
  threshold no mesmo trabalho de medição. Uma mudança de embedding/profile
  requer ADR, re-embedding e novo report por SHA.
- Antes de qualquer upgrade com dados, seguir a regra existente: backup
  verificado, revisão Alembic anotada e restore smoke. Downgrade destrutivo só
  em banco descartável; para dados reais, forward fix ou restore documentado.
- Definir/testar retenção e reaplicação de deletion após restore antes de
  alegar garantia operacional de forget.

## Ações exclusivas do mantenedor

- [ ] Revisar/corrigir os findings em sessões separadas e criar os handoffs
      S04--S06 faltantes.
- [ ] Selecionar um snapshot limpo, revisar paths, efetuar stage/commit e
      fornecer SHA para nova auditoria S07.
- [ ] Aprovar constraints/lock, política de dependências e correção dos CVEs
      do ambiente de build; gerar artifacts novamente a partir do SHA.
- [ ] Executar novamente, sem skips, PostgreSQL integration, MCP E2E,
      migrations down/up e quickstart em ambiente limpo.
- [ ] Revisar privacy/threat model, backup/restore/delete retention, outage,
      security reporting e claim matrix/release notes contra evidências.
- [ ] Somente após GO explícito e autorizações separadas: tag, push final,
      GitHub Release e eventual publicação PyPI.

**Conclusão:** este estado é **NO-GO**. Nenhuma tag, push, GitHub Release ou
PyPI é autorizada por esta auditoria.
