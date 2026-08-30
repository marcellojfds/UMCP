# Plano de execução por sessões — qualidade e Alpha v0

> **Plano histórico de 2026-08-20.** Não reutilize suas branches, sessões ou
> autorizações. Consulte [`CURRENT_STATE.md`](CURRENT_STATE.md).

**Coordenado em:** 2026-08-20
**Repositório remoto:** `https://github.com/marcellojfds/UMCP.git`
**Estado remoto observado:** público, branch default `main`, vazio
**Regra:** cada sessão termina com testes e handoff; commit e push exigem
autorização explícita separada.

## Ordem e modelos

| Sessão | Modelo | Pacote | Dependência | Resultado |
|---|---|---|---|---|
| S00 | Terra | bootstrap Git seguro | nenhuma | baseline local e primeiro push revisado |
| S01 | Luna | higiene estática e warnings | S00 | Ruff/mypy/pytest rápidos verdes |
| S02 | Terra | CI Gate B | S00–S01 | Actions sem Postgres skip silencioso |
| S03 | Terra | corpus e labels W08 | S00, privacy docs | dataset `retrieval-v0` validado |
| S04 | Terra | runner/metrics/report W08 | S02–S03 | decisão objetiva sobre `hash/v1` |
| S05 | Terra | privacy/ops verification | S02, threat model | backup/outage/canary gates verdes |
| S06 | Luna | governança e docs de release | decisões do mantenedor, S04–S05 | RC documentável e publicável |
| S07 | Terra | build/clean-room/auditoria RC | S02, S04–S06 | relatório go/no-go; sem publicação |

S03 e S05 podem ocorrer em paralelo depois de S02. S06 pode preparar arquivos
antes, mas não deve fechar claims sem os relatórios de S04/S05.

## S00 — Git bootstrap seguro (Terra)

Objetivo: conectar o conteúdo local ao remoto vazio sem publicar caches,
secrets ou artefatos temporários.

Passos obrigatórios:

1. Confirmar novamente que a pasta local não é Git e que o remoto continua
   vazio.
2. Inventariar hidden files e criar `.gitignore` para `.env`, `.omp/`, venvs,
   caches Python/testes/typecheck, build/dist, coverage, IDE e exports locais.
3. Rodar secret scan antes de stage.
4. Inicializar `main`, adicionar `origin` e conferir a lista exata de arquivos.
5. Rodar testes rápidos e `./scripts/gate-postgres`.
6. Pedir autorização separada para stage/commit e depois para push.
7. Confirmar no GitHub a revisão inicial e registrar o SHA no handoff.

Não usar `git add .`/`-A`; adicionar somente paths revisados. Se o remoto deixar
de estar vazio, interromper e reconciliar em vez de forçar push.

## S01 — Qualidade imediata (Luna)

- corrigir os dois erros Ruff de `tests/fixtures/domain.py`;
- configurar `asyncio_default_fixture_loop_scope` explicitamente;
- investigar o warning Starlette/httpx sem atualizar dependência às cegas;
- criar um comando/script rápido que rode Ruff, mypy e testes sem DB;
- atualizar contagens dos handoffs sem reescrever evidência histórica.

Aceite: `ruff check .`, `mypy src` e suite rápida verdes; warnings restantes
documentados com owner e ação.

## S02 — GitHub Actions / CI Gate B (Terra)

Criar workflows separados:

- `quality`: Python 3.11, instalação limpa, Ruff, mypy, unit e contract;
- `postgres-e2e`: service PostgreSQL 16 + pgvector pinado, migrations,
  `OMP_REQUIRE_POSTGRES_TESTS=1`, integration e E2E;
- `package`: wheel/sdist, instalação em venv limpa e `pip check`;
- cache somente de dependências; nunca cachear banco, exports ou secrets.

O job Postgres deve falhar se a extensão, migration head ou URL não estiverem
disponíveis. Logs/artifacts passam por canary/secret scan. Definir branch
protection depois do primeiro workflow verde: PR obrigatório e checks
`quality`, `postgres-e2e` e `package` required.

## S03/S04 — Evals (Terra)

Executar exatamente [EVALS_PLAN.md](EVALS_PLAN.md). S03 possui somente dataset,
rubrics, validators e revisão de labels. S04 implementa runner/metrics e executa
o relatório; não altera produção na mesma sessão que mede o baseline.

Se `hash/v1` falhar, abrir ADR separado com opções de embedding e re-embedding.
Não mudar threshold ou corpus no commit do relatório.

## S05 — Privacy, threat model e operações (Terra)

Usar [privacy.md](privacy.md) e [threat-model.md](threat-model.md) como baseline:

- ligar cada claim a teste/comando;
- implementar scan de canário/secrets em CI;
- exercitar outage/readiness/shutdown;
- criar e testar runbooks de backup/restore/delete retention;
- decidir retenção de ledger, logs e backups;
- produzir handoff com riscos aceitos e riscos bloqueadores.

Não implementar auth hosted ou criptografia nesta fase.

## Decisões do mantenedor antes de S06

1. **Licença:** Apache-2.0 é a recomendação para um protocolo/projeto aberto
   porque inclui concessão explícita de patentes; MIT é a alternativa mais
   curta. Confirmar uma delas antes de criar `LICENSE`.
2. **Versão/nome:** manter pacote `open-memory-protocol` e escolher
   `0.1.0a1` para o primeiro RC, ou registrar alternativa.
3. **Idioma:** recomendação: inglês como documentação pública canônica e PT
   preservado para manifesto/contexto.
4. **Security reporting:** habilitar private vulnerability reporting no GitHub
   e definir o contato/prazo público em `SECURITY.md`.
5. **Publicação:** decidir se o Alpha será apenas GitHub Release ou também PyPI.
6. **Budget eval:** aprovar p95 de busca menor que 2.500 ms no ambiente de
   referência e o floor de slice proposto no plano de evals.

## S06 — Governança/documentação (Luna)

Após as decisões, criar `LICENSE`, `SECURITY.md`, `CONTRIBUTING.md`,
`CODE_OF_CONDUCT.md`, `CHANGELOG.md`, support matrix e README/quickstart. Cada
claim deve corresponder ao relatório W08 e à claim matrix de privacidade.
Nenhuma tag ou publicação é autorizada por esta sessão.

## S07 — Release candidate e auditoria (Terra)

- gerar constraints/lock apropriado e artifacts wheel/sdist;
- instalar em Python 3.11 limpo;
- executar quality, Postgres, E2E, eval full, privacy/ops e quickstart;
- auditar licenças/dependências, links, snippets, secrets e conteúdo do pacote;
- gerar relatório `GO`/`NO-GO`, known issues e comandos reproduzíveis.

Tag, GitHub Release e PyPI permanecem ações separadas do mantenedor.

## Prompts curtos para abrir as sessões

### S00 Terra

> Execute S00 de `docs/EXECUTION_PLAN_QA_RELEASE.md`. O remoto é
> `https://github.com/marcellojfds/UMCP.git`. Faça todas as verificações, mas
> peça autorização separada antes de stage/commit e push. Termine com handoff.

### S01 Luna

> Execute S01 de `docs/EXECUTION_PLAN_QA_RELEASE.md`. Limite-se a higiene
> estática, warnings e gate rápido. Não altere semântica de produção.

### S02 Terra

> Execute S02 de `docs/EXECUTION_PLAN_QA_RELEASE.md`. A CI deve falhar sem
> PostgreSQL/pgvector e executar integration/E2E sem skips. Não publique release.

### S03 Terra

> Execute apenas S03 e as seções 2–3/7/9 de `docs/EVALS_PLAN.md`. Crie corpus,
> rubric, schemas e validators antes de qualquer tuning. Não implemente runner.

### S04 Terra

> Execute S04 conforme `docs/EVALS_PLAN.md`, consumindo o corpus congelado.
> Implemente métricas/runner, gere o relatório e não ajuste produção para obter GO.

### S05 Terra

> Execute S05 usando `docs/privacy.md` e `docs/threat-model.md`. Priorize
> evidência automatizada, backup/restore/delete, outage e canary/secret scans.

### S06 Luna

> Execute S06 após ler as decisões explícitas do mantenedor. Crie governança,
> README/quickstart e release docs sem tag, push ou publicação não autorizados.

### S07 Terra

> Execute S07 como auditor independente. Não corrija silenciosamente o RC;
> produza GO/NO-GO, evidência, known issues e próximos passos.

## Registro de execução preservado

### 2026-08-20 — S00 Git bootstrap seguro

- Local inicializado em `main`; `origin` configurado para
  `https://github.com/marcellojfds/UMCP.git` após revalidação de remoto vazio e
  branch default `main`.
- `.gitignore` criado; caches, bytecode, configuração local, exports e
  artefatos permanecem fora do baseline.
- Nenhum path foi staged, commitado ou enviado enquanto se aguardam as
  autorizações explícitas exigidas.
- Gates: mypy e pytest rápido passaram; Ruff tem dois achados mecânicos e o
  gate PostgreSQL falhou porque a extensão `vector` não estava criada no
  container efêmero. Evidência completa em
  `docs/handoffs/alpha/S00-git-bootstrap.md`.
