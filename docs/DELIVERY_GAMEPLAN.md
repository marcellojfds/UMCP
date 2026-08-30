# Gameplan de entrega — Alpha v0 do Open Memory Protocol

> **Plano histórico de 2026-08-20.** Seus status e próximos passos foram
> substituídos por [`CURRENT_STATE.md`](CURRENT_STATE.md) e
> [`roadmap.md`](roadmap.md).

**Status histórico naquele momento:** Fase R implementada; Fases Q/A planejadas e pendentes
**Baseline verificada em:** 2026-08-20
**Objetivo:** levar o estado atual a uma entrega pública local/self-hosted, reproduzível e honesta, sem confundir o Alpha v0 com a visão completa do manifesto.

## Atualização de coordenação — 2026-08-20

A baseline da seção 2 registra o diagnóstico anterior à remediação. Desde então,
R00–R10 foram implementados e o core PostgreSQL foi revalidado em 2026-08-20:

- Docker Engine 27.4.0, PostgreSQL 16.15 e pgvector 0.8.6 disponíveis;
- migrations zero -> `0002_idempotency_operations` verdes;
- `./scripts/gate-postgres`: 11 testes de integração passaram, zero skips;
- gate rápido `./scripts/gate-fast`: 39 testes unitários/contratuais passaram;
- suíte local sem URL de banco: 42 passaram e 12 foram corretamente ignorados;
- Ruff global verde; mypy global verde em 41 source files;
- o remoto público `marcellojfds/UMCP` existe, usa `main` e está vazio, mas a
  pasta local ainda não foi inicializada como repositório Git.

Portanto a Fase R está implementada e possui evidência real. O projeto continua
**bloqueado para release Alpha v0**, não para desenvolvimento: faltam Git/CI,
eval W08, verificação privacy/ops, dependências reproduzíveis, governança e
auditoria de RC. O plano operacional corrente está em
[`EXECUTION_PLAN_QA_RELEASE.md`](EXECUTION_PLAN_QA_RELEASE.md); o desenho do
eval está em [`EVALS_PLAN.md`](EVALS_PLAN.md).

## 1. O que significa “final” nesta entrega

O “final” deste plano é o **Alpha v0**, equivalente ao MVP 0 com Gate B realmente aprovado. Ele demonstra uma fatia vertical persistente:

```text
Cliente MCP A
  -> memory.write explícito
  -> application service
  -> PostgreSQL + pgvector
  -> reinício/reconexão
Cliente MCP B
  -> memory.search relevante ou abstention
  -> memory.update com optimistic concurrency
  -> memory.forget verificável
```

O Alpha v0 deve oferecer:

- servidor MCP local/self-hosted com `memory.write`, `memory.search`, `memory.update` e `memory.forget`;
- PostgreSQL + pgvector como persistência primária do caminho suportado;
- transporte MCP stdio compatível e testado com o cliente oficial;
- SDK Python e CLI finos, sem uma segunda implementação das regras de memória;
- busca baseline versionada, threshold conservador e retorno vazio válido;
- isolamento lógico por `owner_id` no modo local, deixando explícito que o payload é confiado;
- migrations, update versionado, idempotência e forget cobertos no banco real;
- eval baseline, logs sem conteúdo, documentação, runbooks e pacote instalável;
- limitações públicas explícitas.

O Alpha v0 **não** inclui e não deve insinuar:

- writer inteligente ou gravação automática de conversas;
- query expansion, reranking por LLM ou `memory.related` público;
- consolidação de conhecimento;
- autenticação/multi-tenancy hosted, RLS como garantia de tenant ou serviço gerenciado;
- E2EE, zero knowledge, client-side crypto ou busca privada;
- garantia de escala, SLO comercial, UI, graph database ou recursos enterprise.

Essas capacidades permanecem no roadmap pós-alpha, descrito na seção 17.

## 2. Baseline histórica antes da Fase R

### 2.1 Evidência reproduzida

| Verificação | Resultado atual | Leitura correta |
|---|---|---|
| `pytest -q` | 30 passaram, 1 ignorado | Verde apenas para fake/file harness e unit/contract atuais |
| Postgres real | teste ignorado sem `OMP_TEST_DATABASE_URL` | Gate B não executado |
| `ruff check .` | 109 erros | quality gate global vermelho |
| `mypy src` | 17 erros em 6 arquivos | typecheck global vermelho |
| Python | 3.11.8 | compatível com ADR 0001 |
| pacote `mcp` | 1.29.0 instalado | o handoff está desatualizado; runtime não usa o SDK oficial no servidor |
| cliente MCP oficial | handshake/listagem stdio funcionaram na auditoria | compatibilidade smoke, não conformidade completa |
| Git | diretório não é repositório | sem histórico, rollback ou integração segura |
| Docker/Postgres local | daemon/servidor indisponíveis | execução real depende de ambiente a ser preparado |

### 2.2 O que já existe e merece ser preservado

- boundaries `domain -> application <- adapters` e teste de imports;
- aggregate, lifecycle, proveniência, versões e relações;
- ports de repository/UoW/embedding e fake in-memory oficial;
- migration inicial e adapter PostgreSQL/pgvector;
- quatro schemas MCP estritos, envelopes e códigos públicos;
- SDK, CLI, export/import e E2E sobre harness file-backed;
- logging por allowlist e teste de conteúdo-canário;
- ADRs 0001/0002 e contratos internos iniciais.

### 2.3 Bloqueadores reais

1. O entrypoint suportado escolhe `InMemoryMemoryService` ou `PersistentLocalMemoryService`; não compõe `MemoryApplicationService` com `create_postgres_uow_factory()`.
2. O único teste Postgres verifica extensão e tabela. Não exercita repository, application services, busca, concorrência, idempotência, owner isolation, histórico, relações ou forget.
3. `UpdateRequest` e `ForgetRequest` exigem `idempotency_key`, mas os commands internos não a carregam e o gateway a descarta. Update repetido não tem replay estável.
4. O gateway perde `reason_retrieved` e profile produzidos pelo core; o adapter fabrica outra explicação e a versão `baseline.v0`.
5. A CLI usa file harness e define `min_relevance=0`, divergindo do contrato público `0.78`.
6. O transporte HTTP atual é um POST JSON-RPC próprio; não deve ser chamado de MCP Streamable HTTP suportado sem conformidade oficial.
7. Export/import operam somente pela API administrativa do fake/file harness, não pelo caminho Postgres.
8. `docs/protocol.md` foi declarado no handoff, mas não existe. Também faltam `docs/privacy.md`, threat model, evals, CI e governança de release.
9. O corpus e relatório W08 não existem; logo os thresholds de retrieval do Gate B não foram medidos.
10. A licença no `pyproject.toml` é um placeholder e impede um alpha open source correto.

**Conclusão histórica, superseded pela atualização de 2026-08-20:** naquele
momento o estado era um protótipo útil, ainda sem integração real. Hoje o gate
técnico da Fase R está verde; o Gate B global do Alpha continua aberto até
evals, privacy/ops, CI e release engineering ficarem verdes no mesmo RC.

## 3. Princípios de execução

1. **Evidência antes de claim.** Fake, migration offline e handshake isolado não substituem Postgres real + MCP E2E.
2. **Sem skip em gate.** Um teste Postgres ignorado faz o gate falhar, mesmo que o restante passe.
3. **Caminho suportado único.** O default do Alpha usa Postgres. Fake/file ficam explicitamente restritos a testes ou modo demo, nunca fallback silencioso.
4. **Contrato antes de producer/consumer.** Idempotência, transport e DTOs são congelados antes de edits paralelos.
5. **Mudança pequena e reversível.** Cada work package cabe em uma sessão de um executor não-Sol e termina com testes e handoff.
6. **Ownership exclusivo.** Nenhum arquivo é editado simultaneamente por dois modelos.
7. **Precisão antes de recall.** O default permanece `0.78` até mudança baseada em eval e ADR.
8. **Privacidade sem marketing.** No alpha, conteúdo e embeddings são legíveis pelo operador da instância.
9. **Escopo protegido.** Writer, reranking, consolidação e hosted privacy não entram “aproveitando a mudança”.
10. **Publicação é ação do mantenedor.** Executores preparam RC; não criam tag, push, release ou publicação sem autorização.

## 4. Decisões que o mantenedor precisa fechar

As decisões B0 bloqueiam trabalho; as B1 bloqueiam o release, mas não toda a implementação.

| ID | Quando | Decisão | Recomendação deste plano |
|---|---|---|---|
| D01 | B0 | transporte público do Alpha | suportar **stdio somente**; manter HTTP apenas health/readiness até implementar Streamable HTTP oficial |
| D02 | B0 | backend default | Postgres obrigatório; fake/file somente `test`/`demo` explícito |
| D03 | B0 | semântica de idempotência de update/forget | ADR 0003; ledger de operações sem conteúdo para replay de update; definir se forget exige replay idêntico ou apenas efeito idempotente |
| D04 | B0 | retenção do ledger/tombstone mínimo | retenção limitada e documentada; nunca guardar conteúdo, query, provenance ou embedding |
| D05 | B0 | ambiente Postgres suportado | PostgreSQL 16 + pgvector em imagem pinada para local/CI; URL externa também suportada para testes |
| D06 | B1 | profile de embedding do Alpha | medir `hash/v1` primeiro; se falhar Gate B, escolher provider real por ADR, sem reduzir o gate para salvar a demo |
| D07 | B1 | budgets Gate B | aprovar p95, custo e corpus alvo antes de calibrar retrieval |
| D08 | B1 | licença | escolher licença OSI e validar dependências antes do RC |
| D09 | B1 | naming/versionamento | confirmar pacote/repo e usar pre-release coerente, por exemplo `0.1.0a1` |
| D10 | B1 | idioma público | inglês como referência pública, com manifesto PT preservado; ou PT-first explicitamente |
| D11 | B1 | canais | decidir GitHub, PyPI e canal de security disclosure; nenhum é presumido |
| D12 | B0 | versionamento do repositório | mantenedor inicializa Git, registra baseline e habilita política de branches antes de paralelizar edits |

Se D03 ou D04 não forem decididas, a alternativa honesta é remover `idempotency_key` de update/forget antes do primeiro release e versionar o snapshot MCP. Manter um campo obrigatório ignorado não é aceitável.

## 5. Arquitetura alvo do Alpha

```text
Cliente MCP oficial / SDK / CLI
            |
         MCP stdio
            |
       MCPAdapter v0
            |
 MemoryApplicationGateway
            |
 MemoryApplicationService
      |               |
 Hash/real embedding  UnitOfWork
                       |
               PostgreSQL + pgvector
```

Regras de composição:

- `OMP_BACKEND=postgres` é o caminho de release e o default documentado;
- `OMP_BACKEND=memory|file` só é permitido em testes/demo e aparece claramente em status;
- a factory cria e encerra engine/pool sem side effects de import;
- readiness do modo Postgres verifica conexão, extensão e migration head;
- migrations são executadas por comando de operação, não implicitamente por cada processo;
- o servidor não faz fallback para file/memory quando Postgres falha;
- HTTP pode servir liveness/readiness. `/mcp` só é anunciado se passar a suíte oficial do transporte correspondente.

## 6. Caminho crítico e dependências

```text
Decisões D01-D05/D12
  -> contrato de idempotência
  -> suíte real de repository/application
  -> migration/adapter corrigidos
  -> composição Postgres oficial
  -> fidelidade MCP + transporte suportado
  -> SDK/CLI no caminho real
  -> E2E Postgres + cliente MCP oficial
  -> quality/eval/privacy/ops gates
  -> documentação e clean-room RC
  -> Alpha v0
```

Nada depois da composição deve ser aceito contra fake como evidência do Gate B.

## 7. Fase R — Remediation e integração real

### Critério de entrada

- D01–D05 e D12 resolvidas;
- baseline inicial registrada pelo mantenedor;
- um banco descartável acessível por CI ou ambiente local;
- ownership e branches/worktrees atribuídos.

### Work packages

| WP | Escopo de uma sessão | Dono sugerido | Dependências | Saída verificável |
|---|---|---|---|---|
| R00 | ADR 0003 de idempotência, matriz write/update/forget, fingerprint, replay, conflito e retenção | A — Terra backend | D03/D04 | contrato interno aprovado, sem código ambíguo |
| R01 | Propagar idempotency key pelos commands/services/fakes e testes unitários | A — Terra backend | R00 | replay e payload divergente cobertos no core |
| R02 | Criar fixture Postgres descartável e suíte de contrato do repository; ausência de DB deve falhar no modo gate | A — Terra backend | D05 | teste real cria schema e exerce todos os métodos |
| R03 | Corrigir migration/repository para idempotência, concorrência, owner isolation, histórico, relações, filtros e cascade | A — Terra backend | R01/R02 | suite Postgres verde, incluindo corridas |
| R04 | Migration do zero, down/up em DB descartável, profile incompatível e `EXPLAIN` baseline | A — Terra backend | R03 | relatório de migration/índices reproduzível |
| R05 | App factory Postgres: settings, engine lifetime, UoW, embedding, service, gateway e readiness | B — Terra integração | R03 | entrypoint default chega ao repository real |
| R06 | Corrigir mapping MCP: idempotência, reason/profile, errors, timestamps, filtros e defaults | B — Terra/Luna protocolo | R00/R01 | golden contract tests contra o application service real |
| R07 | Fechar stdio com SDK oficial e remover/rebaixar claim de Streamable HTTP | B — Terra protocolo | D01/R06 | smoke oficial de initialize/list/call/cancel; support matrix honesta |
| R08 | SDK/CLI usam servidor/config Postgres; `min_relevance=0.78`; fake/file exige flag demo | B — Luna DX | R05/R07 | quatro comandos atravessam MCP e Postgres |
| R09 | Export/import Postgres via application/admin service, validação total, dry-run e transação idempotente | A core, depois B CLI | R03/R08 | round-trip em instância vazia sem embeddings |
| R10 | E2E canônico com dois clientes, processo reiniciado, DB real, update conflict/replay, forget e canary scan | B — Terra E2E | R05–R09 | jornada completa verde sem fake/file |
| R11 | Handoff de integração com comandos, versões, resultados e débitos | coordenador | R10 | evidência consolidada; ainda não declara Gate B |

### Casos obrigatórios da suíte Postgres

- write e replay concorrente com mesma key criam uma memória;
- mesma key com fingerprint diferente retorna conflito;
- mesma key é independente entre owners;
- update correto incrementa uma vez; replay da mesma operação não incrementa novamente;
- update stale e duas atualizações concorrentes não perdem dados;
- owner B não lê, busca, atualiza, relaciona ou esquece owner A;
- busca combina owner/space/type/state/profile antes de ranking;
- state não ativo fica fora do default;
- histórico contém snapshots esperados;
- relações são owner-scoped e somem no forget;
- forget apaga memória, versões, vetor e relações numa transação;
- repetição de forget segue exatamente o ADR 0003;
- rollback em falha parcial não deixa memória sem vetor ou versão;
- profile incompatível não mistura candidatos.

### Critério de saída da Fase R

- nenhuma tool do entrypoint suportado usa fake/file;
- testes reais de repository/application e E2E passam com zero skips;
- cliente MCP oficial completa as quatro operações;
- defaults e respostas são idênticos em schema, gateway, SDK e CLI;
- `create_postgres_uow_factory()` é exercitado pelo entrypoint e pelos testes;
- export/import não depende do harness local.

## 8. Fase Q — Qualidade, evals, privacy e operações

### Critério de entrada

Fase R verde no ambiente descartável. Trabalho preparatório de datasets/docs pode ocorrer antes, mas resultados do gate usam o binário integrado.

| WP | Escopo de uma sessão | Dono sugerido | Dependências | Saída verificável |
|---|---|---|---|---|
| Q00 | Ruff global por ownership, sem alterar semântica | A/B/C — Luna, cada um em seus arquivos | integração estabilizada | `ruff check .` verde |
| Q01 | Mypy strict, tipos de schemas/transports/SDK/server e warnings pytest | B — Terra/Luna | R07/R08 | `mypy src` verde e warnings avaliados |
| Q02 | Dependências reproduzíveis, lock/constraints, build e instalação limpa em Python mínimo | coordenador + Luna | D08/D09 | wheel/sdist instaláveis e `pip check` verde |
| Q03 | CI com lint, typecheck, unit, contract, Postgres integration, E2E e artifact retention segura | C — Terra CI | R10/Q02 | PR não pode ficar verde com Postgres ausente |
| Q04 | Corpus W08: 25 episódios, 100 memórias, 50 queries, 15 negativas, 10 cross-domain e hard negatives | C — Terra evals | W02 fixtures | dataset versionado, datasheet e splits |
| Q05 | Eval runner e relatório: precision@5, intrusion@5, abstention, slices, p50/p95 e config | C — Terra evals | Q04/R10 | relatório reproduzível hash/profile atual |
| Q06 | Decisão de embedding se baseline falhar; adapter/profile/re-embedding só após ADR | A/C — Terra IR/backend | Q05/D06 | Gate atende ou release fica bloqueado |
| Q07 | `docs/privacy.md`, threat model local, data inventory, retention e claim matrix | C — Terra privacy/docs | R03/R10 | cada claim liga a controle/teste |
| Q08 | Ambiente local pinado, health/readiness, migration/backup/restore e outage runbooks | C — Terra ops | D05/R05 | novo executor sobe e recupera ambiente |
| Q09 | Log/trace canary, secret/PII scan, cardinality e error leakage | C — Luna segurança mecânica | Q07/Q08 | scans verdes no E2E real |

### Gate quantitativo mínimo de retrieval

Conforme W06/W08, salvo ADR baseado em evidência:

- `precision@5 >= 0,80`;
- `intrusion@5 <= 0,10`;
- abstention em queries negativas `>= 0,90`;
- correctness determinístico de lifecycle/isolamento `= 100%`;
- latência e custo reportados com budget aprovado;
- resultados por slice, tamanho da amostra e incerteza publicados.

Se `hash/v1` não atingir o gate, não se ajusta o dataset nem se baixa o threshold para produzir um verde artificial. As opções são escolher um embedding profile melhor com ADR e re-embedding explícito, ou chamar o release de engineering preview e não de Alpha v0/Gate B.

### Critério de saída da Fase Q

- Ruff, mypy e todas as suites verdes;
- CI prova DB real sem skip;
- eval baseline atende o gate aprovado;
- canary e secrets não aparecem em logs, traces ou artifacts;
- runbooks de startup, migration, restart, outage, backup e restore foram exercitados;
- claim matrix limita corretamente privacy e escala.

## 9. Fase A — Release candidate e Alpha público

### Critério de entrada

Fases R e Q verdes, Gate B com evidência assinada pelo mantenedor e D08–D11 resolvidas.

| WP | Escopo de uma sessão | Dono sugerido | Dependências | Saída verificável |
|---|---|---|---|---|
| A00 | Criar `docs/protocol.md` da fonte real, exemplos/goldens e política de compatibilidade | B/C — Luna docs + review Terra | R06/R07 | spec e snapshots sem drift |
| A01 | Architecture, retrieval, privacy, eval report e support matrix | C — Terra/Luna docs | Q05/Q07/Q08 | capacidade atual separada do roadmap |
| A02 | README e quickstart executados do zero; exemplos oficiais de MCP/SDK/CLI | C — Luna DX | A00/A01 | leitor novo reproduz E2E |
| A03 | LICENSE, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, governance e changelog | C + mantenedor | D08–D11 | repositório publicável e canal de segurança real |
| A04 | Build wheel/sdist, instalação em venv limpa, license audit e version matrix | coordenador | Q02/A03 | artifacts reproduzíveis |
| A05 | Auditoria independente do RC contra checklist/DoD, sem corrigir silenciosamente | revisor não autor | A00–A04 | relatório go/no-go e known issues |
| A06 | Tag, release e eventual publicação | somente mantenedor | aprovação A05 | Alpha v0 publicado ou decisão no-go registrada |

### Critério de saída

Uma pessoa sem contexto prévio instala o RC em ambiente suportado, sobe Postgres/pgvector, executa migrations, conecta um cliente MCP oficial, completa o E2E canônico e encontra documentação coerente com o que observou.

## 10. Paralelização com 2–3 executores não-Sol

### Lanes recomendadas

| Lane | Perfil/modelo | Ownership |
|---|---|---|
| A — Core/Postgres | Terra para contratos/concorrência; Luna para mecânica isolada | domain, application, Postgres, embeddings, migrations, unit/integration e contratos internos |
| B — MCP/DX | Terra para transporte/composição; Luna para CLI/docs/formatting | MCP, server, SDK, CLI, contract/E2E, schemas MCP, protocol e examples |
| C — Evals/Ops/Release | Terra para eval/privacy/CI; Luna para datasets/docs/checklists | evals, privacy, ops, runbooks, CI e documentação pública |

### Ondas seguras

1. **Onda 0 — coordenador:** D01–D05/D12, Git/worktrees e R00.
2. **Onda 1:** A executa R01/R02; B prepara R06/R07 sem consumir idempotência ainda; C prepara Q04/Q07 sem editar produto.
3. **Onda 2:** A executa R03/R04; B executa R05 após contrato do core; C executa Q08.
4. **Onda 3:** B executa R08; A e depois B executam as duas metades de R09; C conclui Q04/Q05.
5. **Onda 4:** B executa R10; cada lane fecha Ruff/mypy apenas em seu ownership; coordenador integra e roda todos os gates.
6. **Onda 5:** C/B fecham docs/release em arquivos exclusivos; revisor independente executa A05.

Com apenas dois modelos, unir B e C, mas manter A exclusivo. Com três, nunca pôr dois modelos na mesma árvore de arquivos. Work packages dependentes não devem ser enviados simultaneamente só para aumentar utilização.

## 11. Ownership de arquivos

| Dono | Pode editar | Não pode editar em paralelo |
|---|---|---|
| Lane A | `src/omp/domain/**`, `src/omp/application/**`, `src/omp/adapters/postgres/**`, `src/omp/adapters/embeddings/**`, `migrations/**`, `tests/unit/**`, `tests/integration/**`, `docs/contracts/internal-*`, `docs/memory-model.md` | MCP, SDK, CLI, server, tests contract/E2E |
| Lane B | `src/omp/adapters/mcp/**`, `src/omp/server/**`, `src/omp/sdk/**`, `src/omp/cli/**`, `tests/contract/**`, `tests/e2e/**`, `docs/contracts/mcp/**`, `docs/protocol.md`, `examples/**` | domain/application/Postgres/migrations |
| Lane C | `evals/**`, `tests/evals/**`, `tests/security/**`, `ops/**`, `docs/privacy.md`, `docs/retrieval.md`, `docs/evals/**`, `docs/runbooks/**`, `.github/**` | produto A/B |
| Coordenador | `pyproject.toml`, lock/constraints, `src/omp/config.py`, `tests/conftest.py`, root `README.md`, version/license, status de entrega | qualquer edit concorrente nesses arquivos |

ADRs recebem número e dono antes da execução: 0003 idempotência (A), 0004 composição/transporte (B), 0005 embedding/eval se necessário (C com A). Handoffs usam arquivos únicos para evitar conflito.

Qualquer necessidade fora do ownership vira proposta em handoff. O coordenador muda o contrato compartilhado e só depois libera consumidores.

## 12. Política de Git, branches e commits

Este plano **não executa Git**. A inicialização é decisão e ação do mantenedor.

Política recomendada:

1. O mantenedor faz secret scan, inicializa o repositório e cria um commit imutável `baseline/prototype-audit`.
2. `main` fica protegida; integração ocorre em `integration/alpha-v0`.
3. Cada work package usa branch e worktree próprios, por exemplo `fix/r03-postgres-contract`.
4. Não executar agentes simultâneos em branches diferentes dentro do mesmo diretório físico; usar `git worktree` ou sessões sequenciais.
5. Um commit por mudança lógica; mensagem `fix(core): ...`, `test(postgres): ...`, `docs(release): ...`.
6. Cada branch contém testes e handoff do próprio WP. Não mistura formatting global com mudança semântica.
7. Sem `force push`, rewrite de histórico, commit direto em `main`, credentials, DB dumps ou artifacts com memória.
8. O coordenador integra na ordem das dependências e roda o gate completo após cada merge de contrato.
9. Depois do primeiro release, migrations existentes não são reescritas; apenas novas revisions forward. Antes dele, reescrever `0001` só é aceitável se não houver dados que precisem de upgrade e isso estiver registrado.
10. Tag e publicação pertencem exclusivamente ao mantenedor após A05.

## 13. Cadência de handoff

Cada sessão começa declarando WP, gate, dependências e arquivos owned. Cada sessão termina em `docs/handoffs/alpha/<WP>.md` com:

```text
WP, frente e gate:
Resultado entregue:
Arquivos criados/alterados:
Contratos públicos/internos alterados:
Decisões/ADRs:
Comandos exatos executados:
Resultados, contagens e skips:
Evidência Postgres/MCP/eval:
Riscos ou débitos:
Itens explicitamente não feitos:
Próximo consumidor:
```

Regras:

- “testes passaram” sem comando, ambiente, contagem e skips é inválido;
- skip ou dependência ausente aparece como blocker, não como sucesso parcial;
- o coordenador mantém sozinho `docs/handoffs/alpha/STATUS.md`;
- a cada mudança de contrato, producer e consumer param no boundary, atualizam schema/contract test primeiro e integram em sequência;
- a cada onda, o coordenador executa smoke conjunto antes de liberar a próxima;
- logs brutos só viram artifact depois de scan de conteúdo/secrets.

## 14. Comandos e gates reproduzíveis

Os WPs Q02/Q03 devem consolidar estes passos em um comando canônico, por exemplo `./scripts/gate-b`. Até lá, a sequência de referência é:

### Gate 0 — instalação e estática

```bash
python -m pip install -e '.[dev]'
ruff check .
mypy src
pytest -q tests/unit tests/contract
python -m build
python -m pip check
```

### Gate 1 — migration e Postgres real

```bash
test -n "$OMP_TEST_DATABASE_URL"
OMP_DATABASE_URL="$OMP_TEST_DATABASE_URL" alembic upgrade head
OMP_REQUIRE_POSTGRES_TESTS=1 pytest -q tests/integration
OMP_DATABASE_URL="$OMP_TEST_DATABASE_URL" alembic downgrade base
OMP_DATABASE_URL="$OMP_TEST_DATABASE_URL" alembic upgrade head
```

`OMP_REQUIRE_POSTGRES_TESTS=1` deve transformar DB ausente em erro de collection/setup. O comando de gate deve também confirmar que zero testes foram skipped.

### Gate 2 — MCP E2E real

```bash
OMP_BACKEND=postgres \
OMP_DATABASE_URL="$OMP_TEST_DATABASE_URL" \
OMP_REQUIRE_POSTGRES_TESTS=1 \
pytest -q tests/e2e tests/contract
```

Essa suite deve iniciar/reiniciar processo de servidor, usar ao menos um cliente oficial `mcp`, provar os dois clientes e verificar o canary nos logs.

### Gate 3 — eval/privacy/ops

```bash
python -m evals.run --suite gate-b --output artifacts/evals/gate-b.json
pytest -q tests/evals tests/security
./scripts/scan-artifacts
./scripts/ops-smoke
```

Os nomes finais dos runners podem mudar, mas precisam ser únicos, documentados e usados pela CI. O relatório eval é obrigatório, não substituído pela saída do E2E.

### Gate 4 — release candidate limpo

```bash
python -m build
python -m venv .venv-rc
.venv-rc/bin/python -m pip install dist/*.whl
.venv-rc/bin/python -m pip check
./scripts/quickstart-smoke .venv-rc/bin/python
```

O teste de release roda em DB descartável vazio e sem depender do checkout via `PYTHONPATH=src`.

### Condições objetivas de Gate B

Gate B só é marcado como concluído quando, no mesmo release candidate:

- static, unit, contract, integration e E2E passam;
- nenhum teste obrigatório é skipped ou xfailed;
- migration zero -> head e downgrade/upgrade declarado passam;
- Postgres real + pgvector + MCP oficial completam a jornada;
- cross-owner, conflito, idempotência, forget cascade e abstention passam;
- evals atingem thresholds/budgets aprovados;
- canary/secrets scan passa;
- documentação e claim matrix refletem o binário testado.

## 15. Rollback e recuperação

### Código

- RC mantém a última versão conhecida verde instalável.
- Uma falha antes da publicação reverte a integração do WP, não faz remendos no mesmo commit sem reabrir seus gates.
- Feature experimental fica desligada; o backend suportado nunca cai automaticamente para fake/file.

### Banco

- Toda migration é testada em DB descartável antes de qualquer dado persistente.
- Antes de upgrade em instância com dados: backup verificado, migration revision registrada e restore smoke executado.
- Downgrade destrutivo é permitido apenas no DB descartável. Em dados reais, default é **forward fix** ou restore completo documentado.
- Depois do Alpha, usar estratégia expand/migrate/contract para manter o binário anterior compatível durante rollback.
- Re-embedding usa profile novo e operação retomável; nunca mistura vetores de profiles diferentes nem substitui o índice sem validação.

### Release

- Se A05 encontrar blocker, não criar tag.
- Se problema crítico surgir após tag mas antes de adoção, marcar release como pre-release/yanked quando o canal permitir e publicar known issue.
- Vazamento de conteúdo, cross-owner access, corruption/forget incompleto ou migration não recuperável exigem no-go imediato.

## 16. Riscos e gatilhos de no-go

| Risco | Severidade | Mitigação/gatilho |
|---|---:|---|
| suíte verde escondendo Postgres ausente | crítica | modo gate falha sem DB e com qualquer skip |
| composição ainda usa fake | crítica | teste inspeciona/observa persistência após processo novo e DB diretamente |
| acesso cross-owner | crítica | matriz completa read/search/update/forget/relation/error; qualquer falha é no-go |
| idempotency key ignorada | alta | ADR + replay concorrente no core, Postgres e MCP |
| forget deixa versões/vetores/relações | crítica | cascade test e inspeção SQL após operação |
| custom HTTP anunciado como Streamable HTTP | alta | de-scope para stdio ou suite oficial completa |
| `hash/v1` não entrega utilidade | alta | W08 antes de claim; provider novo só por ADR/re-embedding |
| threshold reduzido para forçar demo | alta | default congelado e mudança somente com relatório/ADR |
| export/import continua fake-only | média/alta | round-trip Postgres em DB vazio antes do release |
| logs/CI artifacts vazam memória | crítica | allowlist + canary/secret scan em suite real |
| dependências sem lock quebram RC | média | constraints/lock e clean install no runtime mínimo |
| trabalho paralelo sobrescreve contrato | alta | worktrees, ownership e integração por ondas |
| release sem licença/security channel | alta | D08/D11 e A03 bloqueiam artifact público |
| docs exageram privacy/hosted | alta | claim matrix W07 comparada automaticamente/manual ao README |

## 17. Roadmap posterior ao Alpha v0

O roadmap só começa depois do Gate B; não faz parte da Definition of Done desta entrega.

| Fase futura | Capacidade | Gate |
|---|---|---|
| MVP 1 | writer em modo `propose`, extração conservadora, dedupe e contradição assistida | Gate C: write precision/recall e unsupported-memory rate |
| MVP 2 | query expansion/reranking, feedback e possível `memory.related` | Gate D: ganho cross-domain sem piorar intrusion/budgets |
| MVP 3 | consolidação auditável, proposals, evidence binding e scheduler externo | Gate E: factual support, utilidade e idempotência |
| MVP 4 | client-side crypto, key lifecycle, embedding location e hosted threat model | Gate F: revisão independente e claims aprovadas |

UI, graph DB, colaboração, billing, multi-region e features enterprise continuam fora até dados do Alpha justificarem sua entrada.

## 18. Matriz de Definition of Done

| Capacidade | Estado atual | Definition of Done do Alpha | Evidência exigida |
|---|---|---|---|
| Instalação | editable install local | wheel/sdist em venv limpa, Python mínimo e dependências reproduzíveis | build + quickstart smoke |
| Arquitetura | boundaries básicos verdes | app factory sem side effects e backend explícito | architecture/config tests |
| Write | unit/fake e repository não exercitado | Postgres transacional, replay concorrente e owner-scoped | integration + MCP E2E |
| Search | fake E2E e core hash unit | pgvector real, filtros, profile, threshold `0.78`, zero-result e métricas | integration + W08 report |
| Update | optimistic concurrency; key descartada | expected version + replay estável + payload conflict | unit/integration/contract/E2E |
| Forget | efeito idempotente no fake/core | cascade real de conteúdo, history, vector e relations; policy de key | inspeção SQL + E2E |
| Owner isolation | alguns testes fake/unit | todas as operações e errors no Postgres/MCP | matriz cross-owner |
| Migrations | SQL offline e presença de tabela | zero->head, constraints, down/up descartável, restore runbook | gate Postgres |
| MCP stdio | custom server e smoke oficial | SDK oficial em initialize/list/call/cancel e quatro tools | compatibility suite |
| MCP HTTP | POST próprio | fora do support matrix ou Streamable HTTP oficial completo | decisão D01/teste oficial |
| SDK/CLI | file harness | quatro operações via MCP/Postgres; JSON/exit codes estáveis | contract + clean E2E |
| Export/import | fake/file | Postgres, dry-run sem mutação, atomicidade, repetição e sem embeddings | integration round-trip |
| Observabilidade | allowlist/teste fake | readiness real, correlation, canary/secret scan e outage behavior | security/ops suite |
| Privacy | limitações em ADR/handoff | data inventory, threat model, retention e claim matrix | review W07 |
| Evals | inexistentes | corpus/splits/runners/report e thresholds aprovados | Gate B report |
| Qualidade | Ruff 109, mypy 17 | Ruff/mypy/testes globais verdes sem skips obrigatórios | CI required checks |
| Documentação | README mínimo; protocol ausente | quickstart, protocol, privacy, retrieval, evals, ops e limitations coerentes | docs/clean-room review |
| Open source | Git/licença/governança ausentes | histórico, licença, security/contribution e changelog aprovados | release audit |

## 19. Checklist de release

### Escopo e claims

- [ ] README chama a entrega de Alpha v0 experimental.
- [ ] Quatro tools e único transporte suportado estão listados.
- [ ] Writer, reranking, consolidation, hosted auth e E2EE estão marcados como futuros.
- [ ] Conteúdo e embeddings legíveis pelo operador local estão explícitos.
- [ ] Escala testada, corpus e budgets são declarados sem extrapolação.

### Produto e banco

- [ ] Backend default é Postgres e não há fallback silencioso.
- [ ] Banco vazio chega ao migration head.
- [ ] Repository/application contract passa no Postgres real.
- [ ] Concorrência, idempotência, cross-owner, histórico, relações e forget cascade passam.
- [ ] Backup/restore e rollback/forward-fix foram exercitados.

### MCP, SDK e CLI

- [ ] Cliente oficial faz initialize, tools/list e as quatro calls.
- [ ] Processo reinicia e outro cliente recupera a memória persistida.
- [ ] Busca irrelevante retorna zero.
- [ ] Conflict/replay de update e repeated forget seguem o contrato.
- [ ] CLI usa `0.78` e `--json`/exit codes passam.
- [ ] Export/import Postgres passa dry-run, round-trip e replay.

### Qualidade, segurança e evals

- [ ] Ruff e mypy verdes.
- [ ] Todas as suites verdes sem skip obrigatório.
- [ ] Gate W08 aprovado com relatório versionado.
- [ ] Canary, secret e PII scans verdes.
- [ ] Errors/readiness não vazam SQL, stack, owner ou configuração.
- [ ] Dependência indisponível não cria retry storm nem fallback inseguro.

### Release engineering

- [ ] Licença escolhida e dependencies auditadas.
- [ ] README/quickstart executados a partir do wheel em ambiente limpo.
- [ ] Version matrix, changelog, known issues e upgrade path publicados.
- [ ] CONTRIBUTING, CODE_OF_CONDUCT e SECURITY têm conteúdo/canais reais.
- [ ] Revisor independente aprovou a matriz DoD.
- [ ] Mantenedor autorizou explicitamente tag e publicação.

## 20. Condição terminal

O trabalho termina quando todos os itens bloqueadores desta checklist estão verdes no mesmo release candidate e a evidência foi registrada. Se Postgres real, evals ou o E2E MCP real não puderem ser executados, o estado correto é **bloqueado para Alpha v0**, não “pronto com limitação”.
