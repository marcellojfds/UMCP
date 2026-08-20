# S01 — quality fast gate

**Data:** 2026-08-20
**Sessão:** S01 — Qualidade imediata (Luna)
**Status:** concluída

## Resultado

O gate rápido global ficou verde sem mudança semântica no produto. Foram
corrigidas as duas ocorrências Ruff da fixture de domínio, o escopo padrão de
loop de fixtures assíncronas foi explicitado e foi criado o comando
`./scripts/gate-fast`.

O handoff solicitado da sessão anterior,
`docs/handoffs/alpha/S00-git-bootstrap.md`, não existe neste workspace. A
baseline documental disponível foi `docs/handoffs/alpha/SOL-QA-RELEASE-PLAN.md`,
que registra a mesma suíte e os mesmos dois erros Ruff. Nenhuma evidência
histórica foi reescrita por causa dessa ausência.

## Arquivos alterados

- `tests/fixtures/domain.py` — `datetime.UTC` e quebra mecânica da linha longa;
- `pyproject.toml` — `asyncio_default_fixture_loop_scope = "function"` e
  `httpx2>=2,<3` no grupo `dev`;
- `src/omp/evals/dataset.py` — correções mecânicas adicionais de Ruff que
  apareceram no lint global após a baseline inicial (sintaxe equivalente e
  quebras de linha; sem alteração de regras ou comportamento);
- `scripts/gate-fast` — novo gate sem PostgreSQL, executável;
- `docs/runbooks/mcp-local.md` e `README.md` — documentação do gate rápido;
- `docs/DELIVERY_GAMEPLAN.md` — contagens correntes atualizadas;
- `docs/handoffs/alpha/S01-quality-fast-gate.md` — este handoff.

Não foram alterados contratos MCP, migrations, retrieval ou tuning. Não houve
commit nem push.

## Investigação Starlette/httpx

O ambiente tinha FastAPI 0.141.1, Starlette 1.6.0 e httpx 0.28.1. O
`starlette.testclient` instalado usa `httpx2` quando disponível e emite
`StarletteDeprecationWarning` ao cair para `httpx`; a própria mensagem pede
`httpx2`. A dependência foi adicionada somente ao grupo de desenvolvimento,
mantendo `httpx` para compatibilidade com versões anteriores do stack.

`httpx2>=2,<3` foi validado em venv temporário (`httpx2 2.12.0`) e a suíte
rápida completa passou sem o warning Starlette/httpx. Nenhum código de produto
importa ou usa o cliente HTTP.

## Comandos e resultados

Os comandos abaixo foram executados na raiz do repositório. Para testar a nova
dependência antes de alterar o ambiente global, o teste foi executado com o
`httpx2` do venv temporário no `PYTHONPATH`.

| Comando | Resultado |
|---|---|
| `ruff check .` | `All checks passed!` |
| `mypy src` | `Success: no issues found in 41 source files` |
| `PYTHONPATH=/private/tmp/omp-s01-httpx2/lib/python3.11/site-packages ./scripts/gate-fast` | `39 passed` |
| `PYTHONPATH=/private/tmp/omp-s01-httpx2/lib/python3.11/site-packages pytest -q` | `42 passed, 12 skipped` |

O gate rápido executa exatamente `ruff check .`, `mypy src` e
`pytest -q tests/unit tests/contract`, sem exigir PostgreSQL. A suíte completa
permissiva mantém 12 skips esperados: um E2E e onze cenários de integração sem
`OMP_TEST_DATABASE_URL`/PostgreSQL disponível. Três testes de avaliação
estrutural presentes no workspace ficam fora do gate rápido unit/contract e
entram nessa contagem completa. O gate PostgreSQL permanece separado em
`./scripts/gate-postgres`.

## Warnings residuais

Nenhum warning foi emitido pelo gate rápido validado nem pela suíte completa
validada com `httpx2` e o escopo de loop configurado. Os 12 skips acima não são
warnings e continuam documentados como dependência de ambiente PostgreSQL.

## Confirmação de semântica

As mudanças em `src/omp/evals/dataset.py` foram limitadas a equivalência de
`isinstance` em Python 3.11, parênteses e quebras de linha exigidas pelo Ruff.
As regras de validação, mensagens, contratos, retrieval, migrations e demais
arquivos de produção não foram alterados. `mypy src`, o gate rápido e a suíte
completa passaram após a mudança.
