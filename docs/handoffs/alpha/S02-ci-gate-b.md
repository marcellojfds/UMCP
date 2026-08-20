# S02 — CI Gate B

**Executado em:** 2026-08-20
**Estado:** workflows e gates locais implementados; sem commit, push, release ou
alteração de branch protection.

## Entrega

Foram criados quatro workflows GitHub Actions, todos para `pull_request` e
push em `main`, com `contents: read` e Python 3.11:

| Check/job | Workflow | O que executa |
|---|---|---|
| `quality` | `.github/workflows/quality.yml` | instalação limpa de `.[dev]`, cache somente de pip, `ruff check .`, `mypy src` e unit/contract |
| `postgres-e2e` | `.github/workflows/postgres-e2e.yml` | serviço pgvector/PostgreSQL 16 por digest, gate zero -> head, integration e E2E |
| `package` | `.github/workflows/package.yml` | wheel + sdist, inspeção de conteúdo, venv limpa, `pip check`, import e `omp --help` |
| `security-artifacts` | `.github/workflows/security-artifacts.yml` | scan fail-closed de paths/segredos rastreados e contrato de canário em logs/envelopes |

`postgres-e2e` usa exclusivamente a imagem pinada
`pgvector/pgvector@sha256:ccc6e83d6e35e931dc7c5def2022729d5a6c370318d099181995567ff1fb4d6b`
e a URL descartável do serviço Actions. Não há fallback para container local,
file ou memória no workflow.

## Gate PostgreSQL

`scripts/gate-postgres` foi fortalecido e é o comando único do job real. Ele:

1. exige conexão com `OMP_TEST_DATABASE_URL` e exporta
   `OMP_REQUIRE_POSTGRES_TESTS=1`;
2. exige especificamente PostgreSQL 16 e que `vector` esteja disponível antes
   da migration e instalado depois dela;
3. executa Alembic `downgrade base` e `upgrade head`, compara `current` com
   `heads` e repete o ciclo após os testes;
4. executa `pytest -q tests/integration tests/e2e` sem permitir skips por
   ausência do banco.

Logo, URL inacessível, servidor fora da major 16, pgvector ausente ou migration
fora de `head` encerram o job antes de qualquer resultado verde de pytest.

## Segurança e artifacts

- `scripts/scan-ci-safety` falha se não houver arquivos rastreados, se houver
  `.env`, banco, dump, export ou artifact local rastreado, ou se detectar
  valores com formato de segredo. Ele imprime somente paths em uma falha de
  segredo.
- O teste de canário existente é executado no job `security-artifacts`; a E2E
  real também contém canário e é executada em `postgres-e2e`.
- O job `package` rejeita paths proibidos e segredos no wheel/sdist antes de
  instalar ou publicar o artifact.
- O único upload é `python-distributions` (`dist/`), com `retention-days: 1`.
  Banco, `.env`, exports, logs e payloads de teste não são enviados nem
  cacheados. O único cache configurado é o de downloads pip, indexado pelo
  `pyproject.toml`.
- Todos os dados dos testes obrigatórios são os fixtures sintéticos já
  versionados; o serviço PostgreSQL é descartável.

## Validação local

| Comando | Resultado |
|---|---|
| `bash -n scripts/gate-postgres scripts/scan-ci-safety` | passou |
| parse Ruby YAML dos quatro workflows | passou |
| `mypy src` | passou: 41 source files |
| `pytest -q tests/unit tests/contract` | passou: 39 testes; 1 warning Starlette/httpx conhecido |
| `pytest -q tests/contract/test_mcp_contract.py -k canary` | passou: 1 teste |
| URL Postgres deliberadamente indisponível + `OMP_REQUIRE_POSTGRES_TESTS=1` | falhou explicitamente na conexão, antes de pytest |
| preflight real de `./scripts/gate-postgres` | passou: PostgreSQL 16.15, pgvector 0.8.6 disponível e Alembic iniciou o ciclo zero -> head |
| `ruff check .` | falhou: 11 ocorrências preexistentes (evals e fixture); CI deve permanecer vermelho até S01/Q00 corrigi-las |
| `python -m build --no-isolation` | não executou: `hatchling` não está instalado localmente; o workflow o instala em ambiente limpo |
| `./scripts/scan-ci-safety` local | falha esperada: não há arquivos rastreados antes do primeiro commit |

O Docker local exigiu acesso adicional ao daemon. O preflight real passou,
mas outras sessões começaram gates no mesmo Compose/porta enquanto a suite
integration/E2E estava em andamento, então não foi possível atribuir um
resultado final exclusivo nem derrubar o ambiente compartilhado. Isso não
altera o comportamento CI: o workflow usa um service container isolado no
runner Actions. Após o primeiro commit, a validação local completa é:

```bash
./scripts/scan-ci-safety
ruff check .
mypy src
pytest -q tests/unit tests/contract
./scripts/gate-postgres
python -m pip install --upgrade pip build
python -m build
```

## Limitações e próximo passo

Não há ainda um lock/constraints completo de dependências; Q02 continua sendo
necessário para reprodutibilidade bit-a-bit. Os workflows já isolam a versão
de Python, o serviço PostgreSQL/pgvector e os comandos de gate, mas resolvem as
faixas declaradas em `pyproject.toml` durante a instalação limpa.

O handoff `S01-quality-fast-gate.md` não estava presente no checkout. Não
foram alterados os arquivos de Ruff fora do escopo da S02, inclusive os do
módulo de evals que aparentam pertencer a outra sessão.

## Branch protection recomendada para `main`

Depois do primeiro push e de uma execução bem-sucedida, configurar manualmente
em GitHub a exigência de pull request e status checks obrigatórios. Tornar
required os contextos de job exibidos pela primeira execução:

- `quality`
- `postgres-e2e`
- `package`
- `security-artifacts`

Para o mínimo já definido no plano, os três primeiros são obrigatórios; manter
`security-artifacts` também obrigatório é a recomendação desta sessão. Exigir
branch atualizada antes de merge e bloquear force-push/deleção de `main` é
coerente com esse gate. Nenhuma configuração de branch protection foi aplicada
nesta sessão, pois isso requer autorização separada do mantenedor.
