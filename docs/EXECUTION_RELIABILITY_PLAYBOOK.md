---
title: UMCP Codex Execution Reliability Playbook
status: accepted
confidence: confirmed
implementation_status: proposed
applies_to_branch: terra-alpha-recovery
evidence_branch: product/integration
evidence_revision: 1bd460e
updated: 2026-08-21
workstreams:
  - delivery
  - quality
  - operations
  - agent-execution
---

# UMCP — playbook de execução confiável pelo Codex

## 1. Origem

Este playbook transforma em regras duráveis as lições do pós-mortem da sessão
Terra de integração local de 2026-08-21.

Fonte branch-scoped:

- `docs/handoffs/productization/SESSION-POSTMORTEM-2026-08-21.md` na branch
  `product/integration`, observada no commit `1bd460e`;
- commits posteriores nessa branch não transformam automaticamente a sessão em
  entrega completa ou release.

O pós-mortem registra trabalho material — dezenas de commits, gateway MCP,
RLS, criptografia, Admin API, web e workers locais — mas também reconhece que o
goal não entregou todo o escopo, misturou frentes demais e não manteve uma
demonstração simples e contínua de progresso.

## 2. Diagnóstico reutilizável

### 2.1 Produção de código não é produção de entrega

Contagem de commits, arquivos e linhas prova atividade, não conclusão. Uma
entrega existe quando há uma jornada executável, um gate atual no HEAD e um
artefato que outra pessoa consegue reproduzir.

### 2.2 Escopo amplo sem WIP limit cria progresso opaco

Alternar entre gateway, auth, RLS, criptografia, Admin API, web, worker e docs
mantém várias dependências parcialmente abertas. O resultado pode acumular
implementação correta sem fechar uma única experiência demonstrável.

### 2.3 Gates históricos envelhecem

Um teste verde em commit anterior é evidência histórica. Depois que paths
afetados mudam, ele não aprova o HEAD. Todo handoff deve distinguir:

- `current`: executado no SHA entregue;
- `historical`: executado antes de mudanças posteriores;
- `not run`;
- `blocked by environment`.

### 2.4 Contexto de worktree é um controle de segurança

A sessão entrou inicialmente na árvore `terra-alpha-recovery` quando deveria
trabalhar em `product/integration`. O erro foi detectado antes da mutação, mas a
lição é permanente: branch, worktree e SHA precisam ser verificados antes de
cada fase mutável e após toda retomada/compaction.

### 2.5 Limitações ambientais devem ser descobertas no preflight

Browser E2E foi tentado tarde e encontrou limites de loopback/process lifetime
e navegação local. Capability probes precisam ocorrer antes de a implementação
depender da ferramenta. Quando o ambiente não suporta o teste, o executor deve
procurar alternativas cedo e preservar a lacuna como `not verified`.

### 2.6 Um goal longo precisa de marcos internos, não de uma sessão monolítica

Persistência ilimitada é útil, mas não elimina a necessidade de checkpoints.
Um único `/goal` pode percorrer todo o roadmap desde que complete, demonstre e
registre um marco antes de abrir o seguinte.

## 3. Unidade obrigatória de progresso

Todo pacote de execução precisa terminar com cinco elementos:

```text
capability → acceptance test → demo → current gates → handoff/commit
```

Se faltar um deles, o pacote permanece `in progress`.

### 3.1 Capability

Um comportamento observável, não somente uma classe ou interface. Exemplo:

> Claude-sim recupera uma memória MBA criada por ChatGPT-sim no mesmo tenant.

### 3.2 Acceptance test

Escrito ou congelado antes do grosso da implementação. Deve falhar pelo motivo
esperado e passar quando a capacidade estiver completa.

### 3.3 Demo

Comando ou fluxo único reproduzível. Não exigir que o revisor combine cinco
logs e vários commits para inferir sucesso.

### 3.4 Current gates

Executados no HEAD do pacote. Gates antigos são citados separadamente.

### 3.5 Handoff e commit

Estado limpo, SHA, evidências, limitações e próximo pacote explícitos.

## 4. WIP limit

### Regra

Um goal mantém somente **um marco demonstrável ativo**.

Trabalho paralelo é permitido apenas quando:

- o contrato está congelado;
- os paths são independentes;
- cada lane tem acceptance test próprio;
- uma lane não impede demonstrar a outra;
- há worktrees distintas quando mais de um executor escreve.

### Proibido

- abrir UI, worker, auth e migrations ao mesmo tempo sem fechar uma jornada;
- alternar de frente para escapar de um teste difícil;
- iniciar próximo marco porque “a maior parte” do atual parece pronta;
- acumular mocks sem um plano de substituição verificável.

## 5. Milestone contract

Antes de editar, o executor escreve no `GOAL-PROGRESS.md`:

- milestone ID;
- user-visible outcome;
- acceptance command;
- paths previstos;
- dependências;
- gate completo;
- condição de rollback;
- o que fica fora do marco.

O contrato só muda quando nova evidência torna o plano inviável. A mudança
precisa ser registrada antes do novo caminho, não retrospectivamente.

## 6. Worktree preflight

Executar no início, após compaction, antes de merge e antes de fase destrutiva:

```text
1. pwd/worktree path
2. git branch --show-current
3. git rev-parse HEAD
4. git status --short --branch
5. git worktree list
6. expected branch/path/SHA match
7. no unrelated user changes
```

Se não corresponder:

- não editar;
- localizar a worktree correta;
- registrar o desvio;
- retomar somente no contexto validado.

Um script fail-closed `scripts/assert-worktree-context` deve ser criado em um
pacote futuro e usado pelos goals autônomos.

## 7. Capability preflight

Antes de depender de Docker, navegador, rede, modelo ou serviço:

- confirmar binário/runtime;
- confirmar permissão;
- executar o menor smoke possível;
- confirmar lifecycle de processos;
- confirmar paths graváveis;
- registrar fallback;
- separar falta de capability de falha de produto.

Para browser E2E, preferir runner que gerencie seu próprio web server e
lifecycle. Se o ambiente ainda impedir loopback, executar testes DOM/unitários,
render estático e deixar browser E2E como lacuna explícita — nunca como pass.

## 8. Gate freshness

Todo handoff usa esta tabela:

| Gate | SHA | Freshness | Resultado | Artifact |
| --- | --- | --- | --- | --- |
| gate-fast | `<sha>` | current | pass/fail | path |
| postgres | `<sha>` | current/historical | pass/fail/not run | path |
| web | `<sha>` | current/historical | ... | ... |
| browser E2E | `<sha>` | ... | ... | ... |

### Regras

- mudança em migrations/repository invalida gate PostgreSQL anterior;
- mudança em MCP/gateway invalida conformance anterior;
- mudança em web/auth invalida browser E2E anterior;
- mudança em dependencies invalida audit/SBOM anterior;
- mudança em eval/retrieval invalida relatório de development para aquele SHA;
- documentação não pode promover `historical` a `current`.

## 9. Detector de estagnação

Uma execução está estagnando quando ocorre qualquer condição:

- três tentativas consecutivas falham pelo mesmo bloqueio;
- oito commits ou mudanças incrementais sem fechar um acceptance test;
- três trocas de subsistema sem demo do marco ativo;
- repetição de gates sem mudança relevante de hipótese;
- handoff/progress não consegue dizer qual comando comprova o resultado;
- contexto ou tokens são consumidos reabrindo documentos sem uma próxima ação
  concreta.

### Resposta obrigatória

1. parar de adicionar features;
2. preservar estado limpo ou criar checkpoint commit;
3. escrever hipótese de causa;
4. reduzir para o menor teste reproduzível;
5. escolher uma de três alternativas seguras;
6. executar a alternativa mais informativa;
7. atualizar milestone contract;
8. retomar ou registrar bloqueio real.

Post-mortem não substitui essa intervenção durante a execução.

## 10. Heartbeat de progresso

Um goal longo deve atualizar `GOAL-PROGRESS.md` quando:

- acceptance test é congelado;
- uma capability se torna demonstrável;
- um gate muda de vermelho para verde;
- um marco fecha;
- uma limitação ambiental é confirmada;
- ocorre compaction/restart;
- o detector de estagnação dispara.

O heartbeat informa evidência, não atividade:

```text
Milestone: M1-B
Outcome: cross-client recall local
Current SHA: ...
Demo: ./scripts/demo-cross-client
Current gates: ...
Next action: ...
Blocked external actions: ...
```

## 11. Demo-first delivery

Cada marco deve criar um entrypoint único, por exemplo:

- `scripts/demo-local-integration`;
- `scripts/demo-cross-client-memory`;
- `scripts/demo-memory-inbox`;
- `scripts/demo-concepts-and-notes`;
- `scripts/demo-backup-delete-restore`.

O script:

- usa apenas dados sintéticos;
- cria/limpa somente recursos descartáveis;
- falha com exit code não-zero;
- imprime resumo sem conteúdo sensível;
- registra versões e SHA;
- pode ser usado por CI e por um humano.

## 12. Separação de adapters locais e produção

Adapters em memória são válidos para demonstrar contratos, mas precisam estar
marcados em código, config, UI e handoff.

Um marco local pode ficar verde com adapters locais quando seu objetivo é
local. Ele não habilita claims hosted. O próximo marco deve possuir uma lista
explícita de substituições:

- mailbox → e-mail provider;
- session store → durable session storage;
- token verifier → OIDC/JWKS;
- LocalDevelopmentKMS → KMS/HSM;
- in-memory queue → durable queue;
- accepted export → encrypted downloadable artifact;
- logical backup test → transport/restore operational evidence.

## 13. Critério de conclusão de sessão

Uma sessão não deve encerrar apenas porque:

- houve muitos commits;
- o token/contexto está longo;
- um post-mortem foi escrito;
- um subconjunto de testes passou;
- adapters locais existem;
- falta infraestrutura externa, mas ainda há trabalho local.

Ela pode encerrar quando:

- o marco ativo está demonstrado e documentado;
- todo trabalho local independente do pacote está completo;
- HEAD está limpo;
- gates atuais estão classificados honestamente;
- próximo marco e dependências estão explícitos;
- ou existe bloqueio externo real após alternativas seguras.

## 14. Aplicação ao goal Luna de longo prazo

O goal Luna que executará `docs/CODEX_DELIVERY_ROADMAP.md` permanece único, mas
deve operar como uma sequência de marcos fechados:

```text
G00 acceptance/demo/gates/handoff
  ↓
G01 acceptance/demo/gates/handoff
  ↓
...
G17 preparation/handoff
```

Ele não pode abrir G(n+1) antes de produzir demo e handoff do G(n), salvo uma
dependência externa que esteja registrada e permita trabalho local claramente
independente.

## 15. Lições que não devem ser distorcidas

- O post-mortem não diz que “nada foi feito”; houve implementação material.
- Também não diz que o roadmap foi entregue; a sessão foi parcial.
- Muitos commits não são inerentemente ruins; são ruins quando não fecham
  marcos observáveis.
- Persistência de goal não autoriza publicação, holdout ou serviços externos.
- Uma branch local integrada não é main, release nem produção.
- Evidência histórica continua útil, mas precisa ser repetida no candidato
  final quando paths relevantes mudarem.

