# S00 — Git bootstrap seguro

**Executado em:** 2026-08-20
**Estado:** pronto para revisão e autorização de stage; nenhum path foi staged,
nenhum commit ou push foi feito.

## Resultado entregue

- Os planos `docs/EXECUTION_PLAN_QA_RELEASE.md`, `docs/DELIVERY_GAMEPLAN.md`
  e `docs/handoffs/alpha/SOL-QA-RELEASE-PLAN.md` foram lidos antes da ação.
- O repositório local foi inicializado em `main` e `origin` foi configurado para
  `https://github.com/marcellojfds/UMCP.git`.
- GitHub foi revalidado: repositório público, `default_branch=main`,
  `size=0`, e `git ls-remote` retornou zero refs.
- Foi criado `.gitignore` para ambientes/configuração local, caches Python,
  build/coverage, IDE, bancos locais, exports e artifacts.
- Nenhum path foi preparado, commitado, enviado, tagueado ou publicado.

## Inspeção de secrets e artefatos

Foram inspecionados arquivos ocultos, caches, bytecode, configurações, arquivos
de ambiente, chaves, bancos locais, dumps, exports e archives. Não havia
`.env`, `.omp/`, chaves privadas, dumps, exports ou credenciais no workspace.

O scanner dedicado não está instalado neste ambiente. O scan por padrões de
chaves/tokens conhecidos e por atribuições de segredo não encontrou segredo
versionável. O único match foi `POSTGRES_PASSWORD: omp_test` em
`ops/postgres/compose.yaml`, credencial deliberadamente efêmera do serviço local
de teste, sem privilégio externo.

## Gates executados

| Comando | Resultado |
|---|---|
| `ruff check .` | **falhou**: 2 ocorrências mecânicas em `tests/fixtures/domain.py` (`UP017` e `E501`) |
| `mypy src` | **passou**: 39 source files |
| `pytest -q tests/unit tests/contract` | **passou**: 39 passed, 1 warning Starlette/httpx; também houve aviso de configuração de `pytest-asyncio` sem escopo explícito |
| `./scripts/gate-postgres` | **falhou antes de migrations/testes**: PostgreSQL 16.15 subiu, mas `pg_extension` não continha `vector`; o script encerrou fail-closed com `RuntimeError: pgvector extension vector is unavailable` |

O Compose efêmero do gate foi limpo pelo trap do script após a falha.

## Arquivos excluídos do primeiro commit

- `.mypy_cache/`, `.pytest_cache/`, `.ruff_cache/` e todos os `__pycache__/`:
  caches e bytecode regeneráveis.
- `.env*` (exceto `.env.example`), `.omp/`, venvs, bancos/dumps locais,
  `exports/` e `artifacts/`: configuração, estado ou saída local que não deve
  entrar no baseline.
- IDE, cobertura e build/dist: metadados e produtos regeneráveis da máquina
  local.

## Riscos e próximos passos

O baseline não deve ser chamado de verde: Ruff e o gate PostgreSQL estão
vermelhos, com os diagnósticos acima. A próxima ação requer autorização
explícita e separada para adicionar somente a lista revisada de paths.
