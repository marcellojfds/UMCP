# Handoff Sol — planejamento das Fases Q/A

## Objetivo

Preparar sessões Terra/Luna independentes para levar a implementação R00–R10
até um release candidate auditável, sem executar nesta sessão mudanças de CI,
eval runner, Git ou publicação.

## Estado verificado em 2026-08-20

- remoto `https://github.com/marcellojfds/UMCP.git`: público, `main`, vazio;
- pasta local: ainda sem `.git`;
- Docker Engine 27.4.0 disponível;
- PostgreSQL 16.15, pgvector 0.8.6 e migration `0002` revalidados;
- `./scripts/gate-postgres`: 11 passed, zero skips;
- suite local: 39 passed, 12 skips por ausência de URL no comando permissivo;
- mypy: verde em 39 source files;
- Ruff: duas ocorrências mecânicas em `tests/fixtures/domain.py`;
- privacy, threat model e plano de eval criados como baselines documentais.

## Artefatos produzidos/atualizados

- `docs/EXECUTION_PLAN_QA_RELEASE.md` — sequência S00–S07 e prompts;
- `docs/EVALS_PLAN.md` — dataset, schemas, métricas, runner, relatório e DoD;
- `docs/privacy.md` — data inventory, retention e claim matrix;
- `docs/threat-model.md` — boundaries, ameaças, controles e no-go;
- `docs/DELIVERY_GAMEPLAN.md` — status corrente e links;
- handoffs R05–R10/Lane B — referências obsoletas corrigidas;
- `README.md` — links para os documentos correntes.

## Decisões pendentes do mantenedor

1. Apache-2.0 (recomendado) ou MIT.
2. Confirmar pacote/nome e versão `0.1.0a1`.
3. Inglês canônico público ou PT-first.
4. Canal de security reporting e private vulnerability reporting.
5. GitHub Release somente ou também PyPI.
6. Budget p95 e floor por slice do eval.

## Próximo consumidor

Abrir S00 com Terra usando o prompt pronto em
`docs/EXECUTION_PLAN_QA_RELEASE.md`. S00 deve revisar secrets/ignore, inicializar
Git e pedir autorização separada antes de commit e push. Depois, S01 pode ser
executada por Luna e S02 por Terra.

## Restrições

Nenhum documento desta sessão declara Alpha pronto. Os documentos de privacy e
threat model ainda exigem verificação operacional S05 e revisão independente.
Nenhuma tag, release, commit ou push foi criado.
