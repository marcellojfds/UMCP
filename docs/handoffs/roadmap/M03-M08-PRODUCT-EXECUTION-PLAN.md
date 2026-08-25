---
title: UMCP M03–M08 Product Execution Plan
status: proposed
confidence: grounded-plan
implementation_status: not-started
scope: product work outside the GCP infrastructure lane
updated: 2026-08-25
owners:
  - Terra: data plane, contracts, security, workers, evals and operations
  - Luna: product experience, web, SDKs, connectors, docs and conformance
---

# UMCP — plano autônomo de execução do produto M03–M08

## 1. Decisão executiva

Este documento é o plano operacional da evolução do produto depois de M02,
sem assumir que a infraestrutura GCP seja produto pronto ou autorização de
release. O objetivo é fechar, em uma sequência de marcos demonstráveis, a
experiência que transforma o Alpha local em um produto de memória portátil:

```text
conectar → consentir → registrar → revisar → recuperar → explicar
       → corrigir → exportar → revogar → esquecer
```

O resultado final esperado é uma pessoa capaz de conectar dois clientes
comprovadamente suportados ao mesmo vault, registrar uma memória consentida,
recuperá-la com provenance e motivo, corrigi-la, exportá-la, revogar uma
conexão e esquecê-la sem vazamento entre tenants. M03–M08 também devem deixar
o produto instalável, observável, avaliável e honesto sobre compatibilidade,
privacidade e limites.

M02 fica classificado neste plano como **infraestrutura de staging recebida
como dependência não verificada para o produto**. O handoff
`docs/handoffs/roadmap/M02-GCP-DEPLOYMENT-DONE.md` é uma declaração de execução
da lane GCP, não evidência de que auth, tenant isolation, MCP remoto,
criptografia, operações de deleção, UX ou compatibilidade estejam prontos. M02
não é release, não habilita claims públicas e não abre beta.

Este plano não autoriza nem propõe deploy, alteração de IaC, Cloud Run, GCP,
workflow, Dockerfile, código de infraestrutura, segredo, API externa,
cobrança, publicação, push, PR, tag ou release. Quando um marco precisar de um
endpoint, identidade, banco, fila, KMS ou serviço hospedado, isso aparece
somente como **dependência fornecida e verificada por outra lane**. O produto
deve continuar demonstrável em adapters locais e dados sintéticos enquanto
essa dependência não estiver disponível.

## 2. Evidência e ponto de partida

### 2.1 Fontes lidas

O plano foi derivado de:

- `docs/PRODUCT_VISION_PORTABLE_MEMORY.md` — north star, jornada, estados,
  espaços, consentimento, provenance, recall e Definition of Done;
- `docs/CODEX_DELIVERY_ROADMAP.md` — marcos M0–M8, owners, gates e backlog;
- `docs/GAMEPLAN_PRODUCTIZATION_TERRA_LUNA.md` — ADRs 0009–0015, ondas,
  compatibilidade, UX e operação;
- `docs/EXECUTION_RELIABILITY_PLAYBOOK.md` — WIP, milestone contract,
  preflight, freshness, demo-first e detector de estagnação;
- `docs/contracts/internal-application-services.md` e
  `docs/contracts/internal-repository.md` — fachada única, owner-scoping,
  idempotência, export/import e transação;
- `docs/contracts/mcp/v0/README.md` — v0 atual: exatamente
  `memory.write/search/update/forget`, stdio e HTTP apenas health/readiness;
- `docs/contracts/cloud-principal-and-jobs-v1.md` e
  `docs/contracts/cloud-migration-plan-v1.md` — contratos de principal,
  envelopes assinados, migração aditiva, RLS e restore/tombstones;
- `docs/handoffs/core-mvp0.md` e `docs/handoffs/mcp-mvp0.md` — base local,
  limites de `owner_id`, harnesses e jornada local;
- `docs/handoffs/productization/P00-baseline-manifest.md` e
  `docs/handoffs/productization/P01-terra.md` — baseline suja, contratos Terra,
  ausência de autorizações externas e claims ainda bloqueadas;
- `docs/handoffs/roadmap/M02-GCP-DEPLOYMENT-DONE.md` — lido apenas como
  contexto de uma lane GCP separada, não como evidência de produto.

Não há no checkout um arquivo de handoff nomeado M01. Essa ausência é uma
lacuna de rastreabilidade, não uma licença para inventar o estado de M01. Os
handoffs locais de core/MCP, P00/P01 e a evidência Alpha são os predecessores
usados neste plano. Um executor deve criar uma reconciliação curta se encontrar
um handoff M01 em outra branch autorizada.

Links locais das fontes usadas: [visão de produto](../../PRODUCT_VISION_PORTABLE_MEMORY.md),
[roadmap de entrega](../../CODEX_DELIVERY_ROADMAP.md),
[gameplan Terra/Luna](../../GAMEPLAN_PRODUCTIZATION_TERRA_LUNA.md),
[playbook de confiabilidade](../../EXECUTION_RELIABILITY_PLAYBOOK.md),
[contrato de application services](../../contracts/internal-application-services.md),
[contrato de repository](../../contracts/internal-repository.md),
[contrato de principal/jobs](../../contracts/cloud-principal-and-jobs-v1.md),
[plano de migração/restore](../../contracts/cloud-migration-plan-v1.md),
[handoff core MVP0](../core-mvp0.md), [handoff MCP MVP0](../mcp-mvp0.md),
[P00 baseline](../productization/P00-baseline-manifest.md),
[P01 Terra](../productization/P01-terra.md) e
[M02 recebido da lane GCP](M02-GCP-DEPLOYMENT-DONE.md).

### 2.2 Estado que permanece verdadeiro

- O Alpha local/self-hosted possui uma base de domínio e quatro tools MCP v0,
  mas não deve ser descrito como produto hosted multiusuário.
- `owner_id` confiado pelo cliente é aceitável somente na composição local
  explicitamente confiável; no hosted, o principal verificado é a fonte da
  identidade e o cliente não escolhe o owner.
- O serviço de aplicação é a fronteira única para MCP, SDK, CLI e HTTP; não se
  deve duplicar regra de negócio em adapters.
- A memória é dado não confiável e nunca deve ser tratada como instrução de
  sistema.
- Conteúdo, provenance e embeddings são sensíveis. O desenho v1 é
  server-decryptable; não habilita E2EE, zero knowledge ou “everything
  encrypted”.
- O candidato E5 tem evidência de desenvolvimento elegível em T03; isso não é
  `GO` de release e não permite abrir o holdout sem autorização separada.
- `candidate`, `confirmed`, `pinned`, `contradicted`, `superseded`, `stale`,
  `archived` e `forgotten` têm semântica de produto; “forgotten” não é um texto
  que possa voltar após restore.
- A evidência histórica de testes continua útil, mas um path alterado invalida
  o gate correspondente até que ele seja executado no SHA entregue.

### 2.3 Evidence labels obrigatórios

Todo handoff de M03–M08 deve classificar cada afirmação como:

| Rótulo | Uso |
| --- | --- |
| `current` | comando executado no SHA entregue, com saída/artifact identificável |
| `historical` | evidência de SHA anterior, preservada apenas como contexto |
| `not-run` | teste previsto, ainda sem execução |
| `blocked-by-environment` | teste não executável por capability ausente, com alternativa tentada |
| `unverified` | declaração recebida de outra lane sem teste do produto |
| `prohibited-claim` | afirmação que não pode aparecer em UI/docs neste estágio |

Nenhum `historical`, `unverified` ou `blocked-by-environment` pode ser
apresentado como `GO`.

## 3. Outcome de produto e invariantes

### 3.1 Journey vertical que todos os marcos preservam

O acceptance central, evoluído de M03 a M08, é:

1. cliente A autoriza uma conexão com scopes mínimos;
2. um trecho explicitamente enviado gera uma memória ou candidato, nunca uma
   captura implícita de transcrição;
3. a política da conexão/espaço determina se a memória fica em `candidate`,
   exige confirmação ou pode ser confirmada automaticamente;
4. o usuário vê origem, tipo, espaço, confiança, importância, policy e
   provenance;
5. cliente B, com a mesma identidade e autorização adequada, busca a memória;
6. o resultado é mínimo e inclui espaço, cliente de origem, timestamp e
   `reason_retrieved`, sem chain-of-thought;
7. outro tenant recebe zero dados e nenhum detalhe revelador;
8. update usa versão/idempotência e não perde histórico;
9. export é owner-scoped, versionado e sem embeddings por padrão;
10. revoke bloqueia a conexão revogada sem retirar acesso de uma conexão ainda
    autorizada;
11. forget remove conteúdo, versões, relações, vetor online e resumos
    derivados; restore reaplica tombstones antes de liberar tráfego.

### 3.2 Invariantes não negociáveis

- **Portabilidade:** o vault pertence ao usuário/tenant, não ao cliente de IA.
- **Minimização:** apenas o trecho explicitamente enviado e a memória útil são
  processados; full transcript não é default.
- **Consentimento:** `disabled`, `manual`, `assisted` e `automatic` são
  políticas explícitas; “não memorize esta conversa” sempre vence.
- **Provenance:** não existe memória relevante sem origem, momento, cliente,
  sessão/conversa quando disponível, policy e versão.
- **Isolamento:** toda leitura, escrita, job, export e delete tem contexto de
  owner/tenant; cross-tenant leakage tem tolerância zero.
- **Idempotência:** replays não criam segunda versão nem segunda deleção;
  fingerprints divergentes retornam conflito opaco.
- **Reversibilidade:** consolidação cria derivados versionados; não destrói
  evidência nem converte hipótese em fato silenciosamente.
- **Honestidade:** compatibilidade é por superfície e data; “compatible” não
  significa “tested”.
- **Privacidade:** logs, métricas, traces, erros, fixtures, screenshots e
  artifacts não contêm conteúdo, query, token, e-mail bruto ou vetor.
- **Fail-closed:** ausência de tenant context, falha de auth, KMS, assinatura,
  expiração ou replay de job falha sem fallback plaintext/demo.

## 4. Mapa M03–M08

| Marco | Outcome observável | Owner primário | Não é permitido declarar |
| --- | --- | --- | --- |
| M03 | Dois clientes reais comprovados completam write/capture → recall → update/forget, com auth, provenance e revoke | Luna; Terra no gateway/contratos | “funciona em todos os chats” |
| M04 | Usuário inspeciona e administra Inbox, Concepts, Mental Notes e Activity em web acessível | Luna; Terra no domínio/API | conceito como verdade não rastreável |
| M05 | Recall útil, abstention e captura controlada medidos em slices pré-registrados, com prompt-injection/memory-poisoning controlados | Terra; Luna em harness/UX | qualidade sem eval, suporte multilíngue amplo ou holdout executado sem autorização |
| M06 | Beta fechado operacional com 5–20 usuários consentidos, suporte, quotas, incident/restore/delete drill e rollback ensaiado | Terra + Luna | abrir usuários externos sem aprovação, dados pessoais antes do privacy gate |
| M07 | Community instalável e reconstruível a partir de SHA, com docs, CI, SBOM, provenance e auditoria independente | Terra + Luna; auditor independente | publicação, tag ou release sem autorização |
| M08 | Public beta/GA somente com compatibilidade, claims, SLO, auth/RLS/crypto, deleção/restore e operação auditados | Terra + Luna; auditor independente | GA por atividade, demo ou deploy GCP |

### 4.1 Sequência de dependências

```text
M02 staging (dependência não verificada, outra lane)
        │
        ├── M03-A contrato/auth/conformance preflight ──┐
        └── M03-B UX/recipes/synthetic harness ──────────┘
                              ↓
                 M03 connector evidence
                              ↓
       ┌──────────────┬───────┴────────┬──────────────┐
       │              │                │              │
   M04 Atlas       M05 evals       M06 beta prep   M07 community prep
   domain+UX       quality+policy  (after M04/M05)  (can start docs)
       └──────┬───────┴────────┬───────┴──────────────┘
              ↓                ↓
          M06 closed beta → M07 RC → M08 decision
```

M04 e a parte local de M05 podem avançar em paralelo depois de M03 fechar os
contratos de provenance, states, scopes e recall. M06 só pode aceitar usuários
depois de M04 oferecer controle compreensível e M05 fechar os guardrails
mínimos. M07 pode preparar documentação, packaging e supply-chain em paralelo,
mas a aprovação de release depende de M05/M06 e auditoria independente.

## 5. Modelo de execução e ownership

### 5.1 Terra high / Luna high

O modelo recomendado é **Terra high** para tudo que pode alterar verdade de
dados, segurança ou operação e **Luna high** para tudo que o usuário vê,
instala ou usa para conectar um cliente. Cada executor deve trabalhar em
worktree própria e consumir o contrato do outro por handoff.

| Área | Owner | Paths primários | Consumidor |
| --- | --- | --- | --- |
| Core, application service, lifecycle, provenance | Terra | `src/omp/domain/`, `src/omp/application/`, `src/omp/adapters/` | Luna via schemas/SDK |
| Gateway, principal, scopes, authz, jobs | Terra | `services/gateway/`, `services/worker/`, contratos/ADRs autorizados | Luna/web/conectores |
| Migrations, repository, RLS, crypto, restore/delete | Terra | `migrations/`, adapters Postgres, runbooks de produto | auditor/ops |
| Retrieval, worker, quality and eval harness | Terra | `evals/`, scripts de eval, worker paths | Luna para UX de estados |
| Web and product UX | Luna | `apps/web/`, component/tests, visual fixtures | Terra APIs |
| SDK Python/TypeScript and recipes | Luna | `packages/sdk-python/`, `packages/sdk-typescript/`, `examples/` | usuários/agentes |
| Compatibility matrix and public docs | Luna | `docs/site/`, docs de integração e matriz versionada | auditor/usuário |
| Product analytics/support surfaces | Luna with Terra privacy review | web analytics schemas, support docs | beta ops |

### 5.2 Paths compartilhados e proibidos

Paths compartilhados só mudam após handoff explícito com diff mínimo, acceptance
test e dono nomeado:

- `pyproject.toml`, locks e manifests de pacote;
- schemas MCP e snapshots JSON;
- `README.md`, docs de claims e compatibilidade;
- `docs/adr/`, migrations e workflows de qualidade;
- arquivos de contrato e manifests de release.

No escopo desta lane, não editar:

- qualquer IaC, Cloud Run, GCP ou deploy;
- `Dockerfile` e scripts de deploy;
- `.github/workflows/` de deploy;
- `src/omp/server/http.py` e outras fontes compartilhadas/GCP recebidas no
  estado atual;
- docs e runbooks exclusivos de GCP;
- worktree original ou paths fora do handoff atribuído.

Se um contrato precisar mudar um path proibido, o executor registra um
`dependency-request` e continua com adapter/mocks tipados que preservem a
interface. Não edita o path proibido para “desbloquear” o marco.

## 6. Regras de WIP, autonomia e checkpoints

### 6.1 WIP limit

Cada goal mantém **um único marco demonstrável ativo**. Paralelismo só é
permitido quando:

1. o contrato está congelado;
2. os paths são independentes;
3. cada lane tem acceptance test e demo próprios;
4. uma lane consegue terminar sem esconder a falha da outra;
5. cada lane escreve em worktree diferente.

É proibido abrir UI, workers, auth, migrations e conectores simultaneamente
sem fechar uma jornada. Um contrato parcial não permite iniciar o consumidor.

### 6.2 Milestone contract obrigatório

Antes de editar, o executor registra no handoff de progresso do próprio goal:

- ID do marco e outcome em linguagem de usuário;
- comando de acceptance e demo único;
- paths previstos e paths explicitamente fora;
- dependências e capability preflight;
- gate completo;
- condição de rollback/forward-fix;
- critério de parada e próximo handoff.

### 6.3 Coordenador autônomo: regras concretas

O coordenador pode operar em background dentro de um worktree autorizado com
esta política determinística:

1. **Preflight:** antes de cada fase, e após compaction, coleta `pwd`, branch,
   SHA, status, worktrees, paths alterados e capabilities necessárias.
2. **Allowlist:** constrói uma allowlist de paths do marco. Qualquer mudança
   fora dela interrompe a lane e pede handoff; não tenta “limpar” o arquivo.
3. **Fila:** mantém no máximo um marco `in_progress`; tarefas paralelas são
   filhas com contratos, owners e comandos separados.
4. **Prioridade:** fecha primeiro o acceptance test do marco; depois corrige
   qualidade, docs e polish. Não troca de subsistema para escapar de um teste.
5. **Evidência:** salva SHA, comando, exit code, resumo redigido e artifact;
   nunca salva payload, segredo ou log bruto sensível.
6. **Freshness:** qualquer mudança em gateway/MCP invalida conformance;
   migration/repository invalida Postgres; web/auth invalida browser E2E;
   eval/retrieval invalida relatório de qualidade; dependência invalida audit e
   SBOM.
7. **Autonomia local:** pode editar paths autorizados, usar dados sintéticos,
   rodar testes e criar commits locais do próprio pacote quando isso estiver
   autorizado. Não faz API externa, deploy, push, PR, cobrança, e-mail real,
   segredo, holdout ou release.
8. **Escalonamento:** para e pede decisão humana somente para provider,
   orçamento, domínio/marca, política de dados, holdout, beta, termos legais,
   risco residual P0/P1 ou mudança de contrato compartilhado.
9. **Bloqueio ambiental:** após três falhas iguais, ou oito mudanças sem
   fechar acceptance, aplica o detector de estagnação: reduz ao menor repro,
   tenta adapter local e registra `blocked-by-environment` se necessário.
10. **Parada segura:** não começa M(n+1) antes de demo, gates atuais, rollback,
    handoff e commit do M(n), salvo trabalho documental independente explicitado.
11. **Sem auto-GO:** o coordenador produz evidência e recomendação; `GO` de
    release requer auditor independente e autorização humana.

### 6.4 Heartbeat de execução

Cada checkpoint deve responder em uma linha a:

```text
Marco | outcome | SHA | demo | current gates | skips/bloqueios | próxima ação
```

Comentários como “implementado”, “deploy ok” ou “muitos testes verdes” não são
heartbeat suficiente.

## 7. Waves paralelizáveis

### Wave 0 — M03 preflight e contrato de produto

**Sequencial.** Terra reconcilia contrato de principal/scopes, states,
provenance e endpoints; Luna congela a matriz de compatibilidade e o roteiro
de UX. A dependência hospedada recebida de outra lane fica marcada
`unverified` até um smoke autorizado e redigido.

**Saída:** acceptance M03, fixture sintético, claim matrix, compatibility
matrix inicial, allowlists de paths e dois worktrees.

### Wave 1 — M03 connectors e conformance

**Paralelizável após Wave 0.**

- Terra: gateway/authz, scopes, revocation, idempotency, error mapping e
  conformance protocol.
- Luna: recipes, SDK clients, prompts, connection UX, matrix e relatórios por
  superfície.
- Auditor: somente leitura dos relatórios e do fluxo final.

**Join:** pelo menos duas superfícies reais diferentes passam a mesma jornada;
uma registra e a outra recupera.

### Wave 2 — M04 Atlas e base M05

**Paralelizável em paths distintos.**

- Terra: concepts, relations, notes, activity receipts, paginated API,
  invalidation e jobs idempotentes.
- Luna: Inbox, Concepts, Mental Notes, Activity, states vazios/erro,
  accessibility e mobile.
- Terra: eval harness de capture/dedup/conflict e slices de policy.

**Join:** UI não fabrica estados; toda inferência exibe suporte e provenance.

### Wave 3 — M05 trusted recall

**Terra high**, Luna em paralelo para feedback UX, instrumentation sem payload e
relatórios. Não abrir o holdout sem autorização. O candidate E5 permanece
congelado para comparação histórica.

### Wave 4 — M06 beta

**Paralelizável após M04/M05 gates mínimas.** Terra fecha quotas, incident,
restore/delete, observability e cost envelopes; Luna fecha onboarding,
feedback, suporte, privacy/security pages e beta notes. Usuários e dados reais
continuam fora sem autorização.

### Wave 5 — M07 community

**Paralelizável com M06 apenas para trabalho local.** Luna fecha quickstart,
SDK/docs e recipes; Terra fecha packaging audit, migrations, recovery docs e
operational evidence. Publicação continua separada.

### Wave 6 — M08 release decision

**Sequencial.** Congelar SHA candidato, executar gates atuais, pedir holdout
separadamente, conduzir auditoria independente, preparar decisão e somente
após autorização humana realizar eventual ação de publicação em outra lane.

## 8. M03 — Cross-client Connectors

### Outcome e escopo

M03 prova portabilidade em superfícies reais, não universalidade. A ordem é:

1. agente Python controlado pelo projeto;
2. ChatGPT developer mode, se a superfície e o endpoint de teste estiverem
   autorizados e disponíveis;
3. Claude API ou cliente oficialmente documentado;
4. Gemini CLI;
5. agente TypeScript.

Cada conector recebe `Supported`, `Experimental` ou `Unverified` com versão,
data, transporte, auth, operações exercitadas, confirmação destrutiva e
limitações. O Secure MCP Tunnel, quando citado, é apenas caminho de teste
privado; não vira endpoint de distribuição por afirmação.

### Tarefas pequenas e ownership

| ID | Tarefa | Owner | Path(s) | Dependência |
| --- | --- | --- | --- | --- |
| M03-01 | Congelar schema de principal, scopes, consent e erro seguro | Terra | `docs/contracts/`, `src/omp/application/` | P01; nenhum hosted claim |
| M03-02 | Adaptar quatro tools v0 sem duplicar service | Terra | `services/gateway/`, adapter MCP autorizado | M03-01 |
| M03-03 | Conformance runner para list/call/error/revoke | Terra | `tests/conformance/`, `scripts/` | M03-01 |
| M03-04 | Fixture sintético write→search→update→forget | Terra | `tests/fixtures/`, `examples/` | contracts v0 |
| M03-05 | SDK Python com auth/config redigida | Luna | `packages/sdk-python/` | M03-01 |
| M03-06 | SDK TypeScript mínimo e recipe | Luna | `packages/sdk-typescript/` | schema estável |
| M03-07 | Recipes por cliente e prompt pack | Luna | `docs/site/integrations/`, `examples/` | capability preflight |
| M03-08 | UX de connection, scopes, revoke e consent | Luna | `apps/web/` | API/contract |
| M03-09 | Relatório datado por superfície e claim matrix | Luna | `docs/site/compatibility/` | execução real |
| M03-10 | Testes adversariais de tenant, scope e replay | Terra | `tests/security/`, `tests/contract/` | principal verificado |

### Acceptance test congelado

Com dados sintéticos e um tenant A/B:

- cliente A registra uma `lesson` no espaço `MBA`;
- cliente B do mesmo tenant recupera a memória com provenance e
  `reason_retrieved`;
- update com versão correta passa, replay idêntico não duplica, versão errada
  falha opacamente;
- forget remove a memória e replay é idempotente;
- tenant B recebe zero e não descobre ID/conteúdo;
- revogar A bloqueia A e mantém B conforme seu scope;
- um cliente sem scope recebe erro seguro;
- cada receita documenta exatamente o que foi testado.

### Comandos de aceitação

Estes comandos são o contrato de execução; só recebem `current` depois de
rodados no SHA do marco:

```bash
git diff --check
PYTHONPATH=src pytest -q tests/contract tests/e2e
PYTHONPATH=src python examples/e2e_two_clients.py
python -m pytest -q tests/conformance tests/security
python scripts/demo-m03-connectors --synthetic --report-dir /tmp/umcp-m03-report
python scripts/check-compatibility-matrix --strict
```

Se algum script novo ainda não existir, o owner deve criá-lo no path autorizado
ou marcar o comando `not-run`; não pode simular sua saída em documentação.

### Gate M03

- duas superfícies reais diferentes completam a jornada, uma escrevendo e outra
  lendo;
- auth, scopes, revoke e confirmação destrutiva foram executados;
- nenhum `owner_id` do cliente hosted concede acesso;
- provenance identifica cliente de origem;
- matriz diferencia Supported/Experimental/Unverified;
- browsers/clients não comprovados não recebem badge de suporte;
- `current` conformance, security, contract e docs/link checks no SHA.

### Rollback M03

- desabilitar o conector por feature flag/matriz sem remover memórias;
- revogar a conexão específica e invalidar tokens/credenciais;
- reverter apenas o adapter/recipe no branch do pacote;
- manter v0 stdio local como caminho demonstrável;
- não fazer downgrade destrutivo de migration; usar forward-fix ou restore
  isolado se o contrato de dados tiver sido alterado.

## 9. M04 — Memory Atlas

### Outcome e escopo

M04 torna a memória navegável fora do chat. O usuário deve conseguir entender
o que foi lembrado, de onde veio, quais conceitos sustentam uma inferência,
quais notas estão fixadas e quais eventos aconteceram. Grafo visual é opcional;
lista textual acessível é obrigatória.

### Tarefas pequenas e ownership

| ID | Tarefa | Owner | Path(s) | Critério |
| --- | --- | --- | --- | --- |
| M04-01 | Modelo `concepts`/`memory_concepts` com provenance | Terra | `src/omp/domain/`, migrations autorizadas | toda aresta rastreável |
| M04-02 | Jobs idempotentes de resumo/recalculation | Terra | `services/worker/`, application ports | retry/restart sem duplicação |
| M04-03 | Invalidação após update/forget/stale | Terra | application/repository/tests | nenhum resumo órfão |
| M04-04 | APIs paginadas de concepts, support memories e relations | Terra | gateway/application contracts | tenant/scope enforced |
| M04-05 | Memory Inbox com candidate origin/reason/policy | Luna | `apps/web/` | confirm/edit/discard real |
| M04-06 | Concepts list/detail/search/filters | Luna | `apps/web/` | teclado/mobile |
| M04-07 | Mental Notes: pin, note, goal, decision, open question | Luna + Terra | `apps/web/`, service contract | lifecycle explícito |
| M04-08 | Activity e `why recalled?` audit-safe | Luna + Terra | web/API/telemetry tests | sem payload/CoT |
| M04-09 | Estados loading/empty/error/offline e reduced motion | Luna | `apps/web/` | não fabrica dados |
| M04-10 | Snapshot/keyboard/axe/link/claim checks | Luna | web tests/scripts | current no SHA |

### Acceptance test congelado

1. inserir três memórias sintéticas em dois espaços, uma candidate, uma
   confirmed e uma pinned;
2. abrir Inbox, editar/confirmar uma candidata e observar efeito no recall;
3. navegar um conceito até as memórias de suporte e provenance;
4. criar Mental Note, relacioná-la a um conceito, pin/unpin e arquivar;
5. abrir Activity e explicar um recall por sinais determinísticos;
6. esquecer a memória de suporte e verificar que relação/resumo desaparecem ou
   ficam explicitamente invalidados;
7. repetir com tenant B e comprovar zero conteúdo;
8. executar tudo por teclado e em viewport mobile declarada.

### Comandos de aceitação

```bash
python scripts/demo-m04-atlas --synthetic --report-dir /tmp/umcp-m04-report
python -m pytest -q tests/contract tests/e2e tests/atlas
python -m pytest -q tests/security -k 'tenant or provenance or forget or audit'
npm --prefix apps/web run lint
npm --prefix apps/web run test
npm --prefix apps/web run build
npm --prefix apps/web run test:e2e -- --grep 'Inbox|Concepts|Notes|Activity'
python scripts/check-accessibility --path apps/web
python scripts/check-claims-and-links --strict
```

### Gate M04

- Inbox altera o estado real e o recall, não apenas a UI;
- concepts e relations são derivados versionados e rastreáveis;
- forget invalida derivados e não deixa arestas fantasmas;
- Mental Notes não mistura espaços sem permissão;
- Activity explica sinais públicos, nunca chain-of-thought;
- teclado, contraste, mobile e reduced motion aprovados;
- states de falha não apresentam dados inventados;
- API, privacy, tenant e web gates estão `current`.

### Rollback M04

- esconder Concepts/graph por flag sem apagar as memórias de origem;
- parar jobs de consolidação e marcar derivados `stale`;
- reverter somente a camada de UI para lista básica de memórias;
- reprocessar resumos a partir das memórias versionadas;
- usar tombstones e forward-fix para mudanças de schema.

## 10. M05 — Trusted Recall

### Outcome e escopo

M05 estabelece confiança operacional e epistêmica: o sistema lembra o que
ajuda, abstém quando não há evidência, não injeta categorias proibidas, não
confunde memória com instrução e deixa o usuário corrigir qualquer inferência.

### Dados e eval governance

O dataset deve ser sintético ou explicitamente autorizado, versionado por
manifest/checksum, separado em development e holdout. Cada slice registra
idioma, espaço, tipo, policy, dificuldade, conflito, idade e superfície.

Slices mínimos:

- positivos de relevância direta e cross-space permitida;
- negativos semanticamente próximos, mas não relevantes;
- memória stale, contradicted, superseded e archived;
- deduplicação e conflito de versão;
- candidate capture com categoria permitida e proibida;
- prompt injection, memory poisoning e instrução dentro do conteúdo;
- cross-tenant, cross-connection e revoke;
- português e inglês em corpora separados, sem claim amplo por inferência;
- latency/queue/cost sob carga sintética declarada.

Métricas mínimas:

- precision@k, useful recall rate e intrusion por slice;
- abstention rate e wrong-memory confirmation rate;
- accept/edit/reject/never-store rate da Inbox;
- stale/contradiction detection;
- provenance completeness e explainability coverage;
- p50/p95/p99 de search/write e tempo de worker;
- cross-tenant leakage e category-policy violation, ambos zero;
- duplicação por retry e deleção ressuscitada após restore, ambos zero.

O holdout continua fechado até haver SHA limpo, candidato congelado, comandos
reprodutíveis e autorização específica para uma única execução. Falha de
holdout é `NO-GO`; não se baixa a meta retroativamente.

### Tarefas pequenas e ownership

| ID | Tarefa | Owner | Path(s) | Saída |
| --- | --- | --- | --- | --- |
| M05-01 | congelar schema/manifest de eval e slices | Terra | `evals/`, docs de governance | checksum |
| M05-02 | medir capture precision/policy | Terra | eval harness/report | report redigido |
| M05-03 | medir dedupe/conflict/stale | Terra | eval harness/domain tests | IDs/scores somente |
| M05-04 | testar poisoning/instruction separation | Terra | security/eval fixtures | fail-closed evidence |
| M05-05 | worker idempotente, retry/DLQ/backpressure | Terra | `services/worker/` | restart/retry proof |
| M05-06 | embedding profile/source_version/stale protection | Terra | application/repository/migrations | versioned vectors |
| M05-07 | UI de confidence, policy, conflict e abstention | Luna | `apps/web/` | copy/UX states |
| M05-08 | feedback de utilidade sem conteúdo em telemetry | Luna + Terra | web/analytics contracts | opt-in aggregate |
| M05-09 | relatório por SHA e claim matrix de idioma | Terra + Luna | `evals/reports/`, docs | current/historical split |

### Acceptance test congelado

- a query irrelevante retorna abstention;
- memória candidate proibida não vira confirmada automaticamente;
- conteúdo que contém “ignore instructions” permanece dado e não altera
  política/role do sistema;
- retry/restart do worker não duplica embedding, relação ou memória;
- update torna vetor anterior stale e recall não retorna stale;
- memória contradita/superseded recebe estado explícito;
- relatório contém dataset/config/threshold/profile/SHA e não contém conteúdo;
- development e holdout têm manifests distintos; holdout não é lido sem
  autorização.

### Comandos de aceitação

```bash
python scripts/eval-capture --dataset evals/datasets/capture-development.jsonl --report-dir /tmp/umcp-m05-capture
python scripts/eval-retrieval --dataset evals/datasets/retrieval-development.jsonl --config evals/configs/retrieval-v*.json --report-dir /tmp/umcp-m05-retrieval
python scripts/eval-security --dataset evals/datasets/security-development.jsonl --report-dir /tmp/umcp-m05-security
python -m pytest -q tests/evals tests/security tests/workers
python scripts/demo-m05-trusted-recall --synthetic --report-dir /tmp/umcp-m05-demo
python scripts/verify-eval-manifest --report-dir /tmp/umcp-m05-retrieval
```

Se os nomes finais de scripts/config ainda não existirem, eles são deliverables
de M05 e devem ser criados antes do gate. Um relatório manual sem manifest,
SHA e comando não fecha M05.

### Gate M05

- thresholds e slices pré-registrados;
- development passa os guardrails definidos sem ajustar o resultado depois;
- candidate E5 e seus limites continuam identificáveis; qualquer novo modelo
  tem seu próprio protocolo;
- capture, retrieval, provenance, stale, policy e poisoning cobertos;
- worker suporta retry/restart/DLQ sem duplicar ou cruzar tenant;
- holdout permanece `not-run` até autorização ou recebe uma execução única
  vinculada ao SHA candidato;
- claims de idioma e qualidade são limitadas ao corpus demonstrado.

### Rollback M05

- desligar auto-capture e voltar a `assisted`/`manual`;
- desabilitar um profile novo sem misturá-lo a vetores incompatíveis;
- reter dados de origem e reprocessar por job versionado;
- parar consolidator/re-ranker e voltar ao recall baseline conservador;
- mover resultados suspeitos para `stale`/`candidate`, nunca apagá-los como
  correção de métrica;
- se a fila falhar, pausar enqueue e manter a API síncrona em modo seguro.

## 11. M06 — Closed Beta

### Outcome e escopo

M06 valida valor e operação com 5–20 usuários consentidos, inicialmente com
dados sintéticos e depois com dados pessoais apenas após privacy gate, termos e
canal de suporte aprovados. É um beta fechado, não anúncio público.

### Tarefas pequenas e ownership

| ID | Tarefa | Owner | Path(s) | Saída |
| --- | --- | --- | --- | --- |
| M06-01 | onboarding guiado e explicação do que é/não é capturado | Luna | `apps/web/`, docs | first-value flow |
| M06-02 | connection setup, scopes, revoke e export/delete UI | Luna | `apps/web/` | control proof |
| M06-03 | quotas, feature flags e kill switches de produto | Terra | gateway/application | tenant-scoped |
| M06-04 | analytics opt-in agregada | Luna + Terra | analytics contract/tests | sem conteúdo |
| M06-05 | admin console operacional sem leitura casual | Terra | ops/admin API | redacted |
| M06-06 | incident, abuse, compromise e security intake | Terra + Luna | runbooks/support docs | channels/process |
| M06-07 | backup/restore/delete drill e tombstone audit | Terra | runbooks/scripts/tests | current evidence |
| M06-08 | capacity/cost/load baseline sintético | Terra | load/eval reports | budgets |
| M06-09 | beta notes, feedback taxonomy e triagem | Luna | docs/support | decision log |
| M06-10 | rollback rehearsal e restore isolation | Terra | runbooks/tests | timed drill |

### Dados e privacidade

- dados sintéticos são default do onboarding e dos testes;
- dados pessoais exigem consentimento claro, minimização, retention e canal de
  deleção definidos;
- analytics não recebe memória, query, provenance bruta, token ou identificador
  direto desnecessário;
- o usuário pode ver policy de captura por conexão e espaço;
- export/download é temporário, owner-scoped e auditado;
- suporte trabalha com IDs redigidos e fixtures, não com vault aberto;
- break-glass, se existir no desenho v1, precisa de justificativa, expiração,
  alerta e registro sem payload.

### Acceptance test congelado

Uma conta beta sintética consegue: conectar, entender o consentimento,
registrar/confirmar uma memória, recuperá-la em outra superfície, corrigir,
pin/unpin, exportar, revogar uma conexão, esquecer e reexecutar restore sem
ressuscitar o conteúdo. O operador consegue observar disponibilidade, fila,
erro, quota e custo agregado sem ler conteúdo casualmente. Um incidente
simulado chega ao canal interno e tem runbook de contenção e rollback.

### Comandos de aceitação

```bash
python scripts/demo-m06-beta-readiness --synthetic --report-dir /tmp/umcp-m06-report
python -m pytest -q tests/beta tests/privacy tests/operations
python scripts/run-restore-delete-drill --synthetic --isolated-target /tmp/umcp-m06-restore
python scripts/run-load-baseline --dataset synthetic --report-dir /tmp/umcp-m06-load
python scripts/check-redaction --artifacts /tmp/umcp-m06-report
python scripts/check-rollback-rehearsal --report /tmp/umcp-m06-report
```

### Gate M06

- 5–20 usuários consentidos somente após aprovação correspondente;
- nenhum P0/P1 aberto, ou exceção formal com owner/data/mitigação;
- onboarding explica captura, recall, provenance, revogação e forget;
- restore e deleção são demonstrados no SHA atual;
- quotas, support, incident e security reporting existem;
- SLO/budgets vêm de observação, não de promessa;
- rollback foi ensaiado e a feature flag de captura pode ser desligada;
- nenhum dado de beta aparece em logs, fixtures, artifacts ou Git.

### Rollback M06

- fechar onboarding e desabilitar novas conexões;
- desligar auto-capture e deixar recall explicitamente consentido;
- suspender writes por tenant afetado sem apagar seu vault;
- revogar credenciais comprometidas e rotacionar por procedimento autorizado;
- restaurar em isolamento, reaplicar tombstones e só então reabrir leitura;
- comunicar internamente a limitação e classificar o incidente antes de retomar.

## 12. M07 — Open-source Release

### Outcome e escopo

M07 prepara a edição Community para instalação limpa e reconstrução
reproduzível. Preparar não é publicar. O artefato precisa poder ser auditado
por SHA, conter apenas dependências, migrations e exemplos permitidos e manter
limitações hosted claramente separadas.

### Tarefas pequenas e ownership

| ID | Tarefa | Owner | Path(s) | Saída |
| --- | --- | --- | --- | --- |
| M07-01 | quickstart local com Postgres/pgvector e stdio | Luna | `README.md`, docs/site | clean install |
| M07-02 | SDK/agent examples Python e TypeScript | Luna | `packages/`, `examples/` | recipes |
| M07-03 | migration upgrade/rollback/restore docs | Terra | `docs/runbooks/`, migrations docs | forward-fix policy |
| M07-04 | packaging wheel/sdist e constraints | Terra | packaging manifests/scripts | reproducible build |
| M07-05 | license, governance, contributing, code of conduct | Luna | root/docs | legal review pending |
| M07-06 | SECURITY, disclosure e vulnerability process | Terra + Luna | root/docs | channel/process |
| M07-07 | required quality/security checks | Terra | quality config/scripts | current evidence |
| M07-08 | SBOM, dependency audit, artifact manifest | Terra | release tooling/docs | checksums |
| M07-09 | compatibility/docs/claim link audit | Luna | docs/site | no stale claim |
| M07-10 | independent RC review | auditor | handoff only | GO/NO-GO |

### Supply chain e instalação

- rebuild de SHA limpo em ambiente declarado;
- wheel/sdist/container, quando aplicável à edição Community, não carregam
  modelos, datasets, secrets, dumps ou reports sensíveis;
- SBOM CycloneDX/SPDX, dependency/license/secret scans e checksums;
- instalação limpa nas plataformas realmente declaradas;
- migrations são explícitas; downgrade destrutivo é proibido;
- docs não confundem adapter demo com persistence de release;
- o usuário sabe que o operador self-hosted pode acessar conteúdo no v1.

### Comandos de aceitação

```bash
git diff --check
python -m build
python -m pip install --no-deps --target /tmp/umcp-m07-install dist/*.whl
python scripts/verify-package-contents --path dist
python scripts/generate-sbom --output /tmp/umcp-m07-sbom.json
python scripts/scan-ci-safety
python scripts/scan-runtime-output --synthetic
python scripts/check-clean-install --workdir /tmp/umcp-m07-clean
python scripts/check-docs-links --strict
python scripts/check-claims-and-links --strict
```

Os comandos acima não são evidência remota de CI; a lane de release precisa
repetir os checks no SHA candidato e registrar a diferença entre local e
remoto. Nada neste plano autoriza upload ou publicação.

### Gate M07

- instalação limpa e quickstart reproduzíveis;
- Community mantém stdio e jornada local documentada;
- artifacts vinculados ao SHA e checksummed;
- CI/required checks e proteção de branch, se existirem, são evidência separada
  e atual, não inferida de arquivo de workflow;
- security reporting, governance, license e changelog revisados;
- auditor independente registra `GO` do RC ou `NO-GO` com findings;
- publicação continua autorização humana separada.

### Rollback M07

- não publicar artifact candidato até auditoria;
- retirar/arquivar localmente o candidato e reconstruir de SHA anterior limpo;
- corrigir forward em migration e versionar upgrade path;
- se uma dependência falhar audit, pin/rebuild em novo candidate SHA;
- manter documentação do Alpha anterior até o novo caminho passar clean install.

## 13. M08 — Public Beta e GA

### Public Beta

Public beta só é uma decisão possível depois de M06 e M07. Requisitos:

- onboarding self-service testado nas superfícies anunciadas;
- conectores Supported datados e comprovados;
- quotas, custos, suporte, status e abuse controls operacionais;
- privacy, subprocessors e retention publicados após revisão apropriada;
- monitoring/alerting e incident drills atuais;
- feedback loop e caminho de revogação/forget funcionando;
- usuário consegue instalar Community e entender a diferença para hosted;
- claims de criptografia limitadas à evidência: em trânsito/repouso e per-tenant
  keys somente se gates correspondentes existirem.

### GA

GA requer, no mesmo SHA candidato ou evidência explicitamente vinculada:

- P0/P1 fechados ou aceitos formalmente com mitigação e data;
- M03 conformance e matriz atual;
- M04 Atlas acessível e rastreável;
- M05 evals, quality, policy e holdout conforme autorização;
- M06 beta SLO, restore/delete, support e rollback;
- M07 clean build, supply-chain e auditoria independente;
- auth/OIDC/OAuth, scopes, consent, revocation, RLS e crypto auditados;
- backup/restore reaplica tombstones e não ressuscita forget;
- claims públicas revisadas linha a linha contra testes;
- canal de suporte e security reporting ativos;
- autorização humana explícita para release, tag, site, package, container e
  abertura pública.

### Acceptance decision commands

```bash
python scripts/release-preflight --candidate-sha <SHA>
python scripts/check-gate-freshness --manifest docs/handoffs/roadmap/M08-gates.json
python scripts/check-claims-and-links --strict
python scripts/check-compatibility-matrix --strict --as-of <DATE>
python -m pytest -q
```

O holdout, se autorizado, terá um comando e uma execução única documentados no
handoff do candidato. Sem essa autorização, o resultado é `not-run`, não
`pass`.

### Rollback M08

- parar novos signups/connections por feature flag;
- retirar uma superfície específica da matriz para `Experimental`/`Unverified`;
- revogar credenciais afetadas;
- voltar a captura para `manual` ou desabilitar;
- restaurar isoladamente e reaplicar tombstones;
- retirar um artifact/site de distribuição somente com autorização da lane de
  publicação, mantendo registro do motivo e do SHA.

## 14. SDKs, UX e conectores — critérios transversais

### SDKs

SDKs Python/TypeScript devem ser finos: transport, auth/config, typed DTOs,
timeouts, idempotency, erro estável e redaction. Não podem reimplementar
lifecycle, ranking, state machine ou autorização. Cada SDK deve oferecer:

- `search` read-only;
- `write`/`capture` com provenance e policy;
- `update` com expected version/idempotency;
- `forget` com confirmação explícita;
- export somente no scope adequado;
- exemplos offline/local e recipe hosted quando a dependência for verificada;
- testes de timeout, replay, revoke, scope e erro opaco.

### UX

Toda tela de memória mostra, na medida mínima necessária: tipo, state, espaço,
origem, data, confidence/importance, policy e ações possíveis. A UI deve
explicar:

- que o cliente decide o que enviar ao MCP;
- que UMCP não vê automaticamente todas as conversas;
- que o servidor v1 processa dados para retrieval;
- como confirmar, corrigir, exportar, revogar e esquecer;
- quando a memória é hipótese, stale, contradita ou derivada.

Destructive actions têm confirmação, reauth quando aplicável, idempotency key,
resultado auditável e estado pending/complete/error.

### Connectors

“Supported” só existe após `write/capture → search → update → forget`,
revocation e erro de scope executados na superfície e versão declaradas. A
matriz deve conter data, transporte, auth, limitações, recipe e report ID.
“MCP-compatible” é uma expectativa de protocolo, não evidência de integração.

## 15. Privacidade, operações e observabilidade transversais

### Data handling

Antes de cada nova categoria ou worker, o owner registra: origem, finalidade,
base de consentimento, retenção, espaço, exposição, export, delete e logs.
Categorias proibidas por padrão continuam sendo credenciais, pagamento completo,
segredos de terceiros e dados médico/jurídico sem escolha explícita.

### Jobs e recuperação

Jobs recebem envelope tenant-bound, verificam assinatura/expiry/nonce/dedupe e
falham em DLQ segura se o contexto for ausente. Retry tem limite e backoff;
não há retry de trabalho não autorizado. Restore ocorre em isolamento, valida
revision/inventory, reaplica todos os tombstones mais novos que o backup,
valida acesso a keys/RLS e só então libera tráfego.

### Observabilidade

Métricas permitidas: contagens agregadas, latência, status, queue depth,
retries, DLQ, quota, disponibilidade, uso por tenant pseudonimizado e
consentido. Proibidos: conteúdo, query bruta, provenance sensível, vetor,
token, e-mail ou prompt. Cada release roda scanner de canário em logs, traces,
erros, artifacts e screenshots.

### SLOs propostos, não prometidos

Somente depois de medir staging/self-hosted em carga declarada, considerar:

- data plane mensal `>=99.9%` no beta;
- search p95 `<=750 ms` na carga beta declarada;
- write síncrono p95 `<=500 ms` com embedding assíncrono configurado;
- 5xx `<0.5%` fora de incidentes declarados;
- RPO `<=24h`, RTO `<=4h` no beta;
- cross-tenant leakage e category-policy violation zero.

Os números acima são metas para validação, não claims atuais nem uma instrução
de deploy.

## 16. Template de handoff por marco

Cada M03–M08 deve produzir `docs/handoffs/roadmap/<milestone>-<lane>.md` ou
equivalente autorizado contendo:

```text
Milestone / outcome:
Base SHA e candidate SHA:
Worktree / branch:
Paths alterados e paths intocados:
Contrato consumido/publicado:
Acceptance test congelado:
Demo única:
Gate freshness table:
  gate | SHA | current/historical/not-run/blocked | resultado | artifact
Dados/evals e holdout status:
Privacy/data handling:
SDK/UX/compatibility evidence:
Rollback/forward-fix:
Falhas, skips e riscos residuais:
Claims habilitadas e claims proibidas:
Dependências de outra lane:
Próxima wave que pode abrir:
Autorização necessária:
```

O handoff não deve incluir secrets, payloads, links de credenciais, logs
integrais ou dados de usuários.

## 17. Primeira wave ex-GCP que pode ser aberta imediatamente

A próxima wave produtiva, independente de qualquer ação GCP, é **M03-W0 —
connector contract and local conformance preflight**:

1. Luna congela a compatibility matrix inicial com todas as superfícies como
   `Unverified` até execução real;
2. Terra congela o acceptance fixture sintético para principal, scopes,
   provenance, revoke, idempotency e erro seguro;
3. ambos executam capability preflight dos runtimes/SDKs já disponíveis,
   sem rede externa e sem dados reais;
4. Luna prepara recipes e UX em mock tipado, sem fingir endpoint hosted;
5. Terra implementa/fecha conformance sobre adapters locais autorizados;
6. o coordenador fecha um demo local de duas superfícies simuladas, classifica
   toda evidência e publica o handoff M03-W0;
7. somente depois de um contrato verde uma lane separada pode fornecer um
   endpoint/credencial de staging para validação real.

Acceptance inicial:

```bash
git diff --check
PYTHONPATH=src pytest -q tests/contract tests/e2e
PYTHONPATH=src python examples/e2e_two_clients.py
python scripts/demo-m03-connectors --synthetic --local-only --report-dir /tmp/umcp-m03-w0
```

Se `scripts/demo-m03-connectors` ainda não existir, sua criação é a primeira
tarefa autorizada da wave; seu report deve dizer `local-only`, não `Supported`.

## 18. Checklist final do programa

Antes de recomendar qualquer abertura pública, o coordenador verifica:

- [ ] M03 tem dois clientes reais comprovados ou limitações explicitamente
  publicadas;
- [ ] M04 Inbox, Concepts, Mental Notes e Activity são utilizáveis;
- [ ] M05 mede qualidade, abstention, policy, provenance e poisoning;
- [ ] holdout está fechado ou tem execução autorizada única no SHA candidato;
- [ ] M06 beta tem consentimento, support, quotas, drills e rollback;
- [ ] M07 Community instala e reconstrói de SHA limpo;
- [ ] M08 tem auditoria independente e claims revisadas;
- [ ] tenant isolation, revoke, export, forget e restore sem ressurreição;
- [ ] logs/artifacts não contêm dados sensíveis;
- [ ] nenhum path GCP/deploy foi alterado pela lane de produto;
- [ ] cada gate está `current`, ou a lacuna está explicitamente marcada;
- [ ] decisões humanas restantes estão listadas e não inferidas;
- [ ] publicação, push, PR, tag, release, cobrança e beta permanecem
  autorizações separadas.

**Conclusão:** este plano está pronto para execução autônoma local a partir de
M03-W0. Ele não declara nenhum marco M03–M08 concluído, não promove M02 a
release e não substitui a auditoria independente nem as autorizações humanas
de infraestrutura, holdout, beta ou publicação.
