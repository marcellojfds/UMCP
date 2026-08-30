---
title: UMCP Codex Delivery Roadmap
status: historical
confidence: confirmed
implementation_status: superseded
applies_to_branch: terra-alpha-recovery
updated: 2026-08-21
workstreams:
  - delivery
  - product
  - security
  - web
  - operations
---

# UMCP — roadmap de entregas pelo Codex

> **Archived plan (2026-08-21).** Do not use this file as current status or
> dispatch instructions. See [`CURRENT_STATE.md`](CURRENT_STATE.md) and
> [`roadmap.md`](roadmap.md).

## Checkpoint operacional — encerramento de 2026-08-21

O estado canônico local ao encerrar o dia é `roadmap/integration` no commit que
contém este checkpoint. O M00 foi integrado e demonstrado, mas **M01 continua
fechado**. A auditoria independente em
`roadmap/luna-verification:docs/handoffs/roadmap/M00-POST-INTEGRATION-VERIFICATION.md`
registrou `M01_NOT_READY` porque:

- duas assertions de sincronização ainda descrevem o estado pré-integração;
- o commit do primeiro protótipo de coordenação foi criado depois do SHA
  auditado e ainda não foi testado no mesmo candidato;
- browser E2E e dependency audit continuam corretamente classificados como
  `environment-blocked`.

O diário completo, incluindo SHAs, gates, tentativas de coordenação e o estado
seguro para retomada, está em `docs/work-journal/2026-08-21.md`.

### Ordem obrigatória na próxima retomada

1. Reproduzir e corrigir apenas as duas assertions obsoletas, preservando o
   comportamento fail-closed.
2. Testar correção e infraestrutura de coordenação em um único SHA limpo.
3. Executar uma nova verificação independente do readiness M00.
4. Integrar o candidato e a evidência somente se a recomendação for `READY`.
5. Criar `M00-READY.md` na lane de integração.
6. Somente então congelar `M01-CORE-CONTRACT.md` e abrir M01.

### Coordenador autônomo — status e redesenho obrigatório

O protótipo `UMCP Agent Coordinator` está **pausado**. Não deve ser reativado
antes de revisar seu desenho. Os experimentos provaram que:

- tasks `/goal` mantidas em terminais podem continuar registradas como
  `active writer` mesmo após exibirem achieved, stalled ou blocked;
- `send_message_to_thread` não é um mecanismo confiável para reativar essas
  sessões interativas;
- criar uma task Codex nova funciona, mas a worktree gerenciada começa em
  detached HEAD e precisa de reconciliação explícita entre task, commit e ref;
- a decisão de transição precisa ler o handoff independente mais recente antes
  de inferir que o próximo milestone está aberto.

O desenho v3 deve usar uma máquina de estados explícita e tasks novas, curtas e
idempotentes por fase. Cada transição precisa registrar `CLAIMED`, task/branch,
SHA final, handoff validado e `DONE`/`BLOCKED`. O mural Markdown permanece útil
como interface humana, mas nunca substitui Git, gates ou handoffs.

## 1. Objetivo

Este roadmap transforma a visão de memória portátil em pacotes executáveis pelo
Codex. Cada pacote produz uma entrega vertical verificável, commits locais,
handoff e gates. Nenhum pacote pode declarar `GO` apenas por adicionar código ou
documentação.

Documento de produto associado:

- `docs/PRODUCT_VISION_PORTABLE_MEMORY.md`.

Gameplan técnico associado:

- `docs/GAMEPLAN_PRODUCTIZATION_TERRA_LUNA.md`.

Playbook de execução, obrigatório para todos os goals:

- `docs/EXECUTION_RELIABILITY_PLAYBOOK.md`.

## 2. Estado de partida

### Verificado no baseline `terra-alpha-recovery`

- Alpha local/self-hosted Python;
- PostgreSQL + pgvector;
- MCP stdio;
- tools v0 write/search/update/forget;
- trabalho semântico E5 development eligible;
- ADRs Cloud 0009–0015;
- contratos iniciais Cloud;
- branches locais de Terra, Luna e integração.

### Evidência branch-scoped da integração Terra

A branch `product/integration` contém uma implementação local material e um
pós-mortem em `docs/handoffs/productization/SESSION-POSTMORTEM-2026-08-21.md`.
O documento registra que a sessão não entregou todo o objetivo, misturou muitas
frentes e deixou parte das gates apenas como evidência histórica. Essa branch
não é tratada aqui como merged em main, released, production-ready ou aprovada.

O primeiro executor deve auditar o HEAD efetivo da branch, repetir gates
afetadas e produzir uma demonstração única antes de abrir novas frentes.

### Proibições preservadas

- holdout sem autorização específica;
- claims de release ou produção sem auditoria;
- E2EE/zero knowledge no v1;
- publicação, push ou serviços externos sem autorização;
- uso de segredo comprometido;
- inferir que MCP recebe transcrições completas.

## 3. Modelo de execução Codex

### Papéis

| Papel | Modelo preferido | Responsabilidade |
| --- | --- | --- |
| Arquiteto/data plane | Terra | domínio, gateway, auth, tenancy, crypto, workers, ops |
| Produto/ecossistema | Luna | web, UX, docs, SDKs, conformance, visual QA |
| Auditor independente | Sol ou Terra em sessão limpa que não foi autora | segurança, gates, evidência e decisão GO/NO-GO |

### Regras por goal

- um objetivo vertical e mensurável;
- ler visão, roadmap, ADRs e handoff anterior;
- ler e obedecer `docs/EXECUTION_RELIABILITY_PLAYBOOK.md`;
- worktree exclusiva;
- validar worktree/branch/SHA antes de toda fase mutável e após compaction;
- autorização local prévia explícita;
- commits locais pequenos e coerentes;
- WIP limit de um marco demonstrável;
- acceptance test congelado antes da implementação principal;
- demo reproduzível antes de abrir o próximo marco;
- testes focados durante implementação e suite proporcional no HEAD final;
- classificar gates como current, historical, not run ou environment-blocked;
- handoff com SHA, comandos, resultados, skips, claims e próximos bloqueios;
- atualizar `GOAL-PROGRESS.md` por evidência, não por atividade;
- acionar o detector de estagnação do playbook;
- não parar na primeira falha;
- não esperar outro executor enquanto houver trabalho independente;
- ações externas continuam separadas.

### Cadência

```text
milestone contract → acceptance test → implementação → demo → gates atuais
→ handoff/commit → próximo marco → integração → auditoria
```

Não iniciar duas implementações sobre o mesmo contrato instável. Terra publica
o contrato; Luna consome; integration verifica ambos.

Um goal pode durar por tempo indeterminado, mas não pode manter vários marcos
parcialmente abertos. Longa duração aumenta a obrigação de checkpoints; não a
remove.

## 4. Escada de releases

| Marco | Nome | Resultado observável |
| --- | --- | --- |
| M0 | Integration Recovery | branches atuais integradas e suite local confiável |
| M1 | Portable Memory Local | dois clientes simulados compartilham vault isolado |
| M2 | Identity & Hosted Alpha | login, OAuth MCP e tenant Cloud em staging |
| M3 | Cross-client Connectors | pelo menos duas superfícies reais comprovadas |
| M4 | Memory Atlas | Inbox, Concepts, Mental Notes e provenance utilizáveis |
| M5 | Trusted Recall | captura/consolidação/retrieval com qualidade e controle |
| M6 | Private Managed Beta | usuários consentidos, operação e suporte reais, sem distribuição pública |
| M7 | Open-source Release (após M6) | Community reproduzível e supply chain auditada |
| M8 | Public Beta/GA | claims, SLOs, compatibilidade e segurança auditados |

### Estratégia de disponibilidade

O primeiro uso externo é um **private managed beta**, não uma distribuição
open source. Até o Gate M6, código, serviço, conectores e documentação
operacional ficam privados e disponíveis somente a operadores do projeto e a
5–20 convidados consentidos. M7 continua obrigatório, mas começa após a
operação/auditoria do beta privado; não bloqueia M6. A decisão e os guardrails
estão em [ADR 0017](adr/0017-private-managed-beta-before-community-release.md).

## 5. M0 — Integration Recovery

### Objetivo

Transformar os trabalhos Terra/Luna já existentes em um único RC local, sem
confundir primitives e shells com funcionalidade completa.

### Executor

- Terra como integrador;
- auditor separado ao final.

### Entregas

- merge local de `product/terra-data-plane` e `product/luna-experience`;
- MCP Streamable HTTP `/mcp`;
- Principal e auth dev fail-closed;
- migrations iniciais de tenant e RLS;
- encryption integrada ao caminho Cloud, não somente classe isolada;
- Admin API local;
- web adapter conectado;
- scripts reais de build/test web;
- conformance local;
- `TERRA-DONE.md` e `INTEGRATION-RC.md`.

### Gate M0

- worktree integration limpa;
- unit/contract/PostgreSQL/MCP E2E verdes;
- web build/test/check verdes;
- owner forjado rejeitado;
- cross-tenant zero leakage;
- ciphertext testado;
- nenhum mock apresentado como produção;
- auditoria independente registra findings.

## 6. M1 — Portable Memory Local

### Objetivo

Demonstrar a principal história de produto sem depender de serviços externos.

### Cenário obrigatório

1. `chatgpt-sim` autentica como usuário A;
2. captura uma lição no espaço MBA;
3. a memória entra como candidate;
4. usuário confirma pela Memory Inbox;
5. `claude-sim` autentica como o mesmo usuário/tenant;
6. pergunta sobre um problema de trabalho relacionado;
7. recall encontra a lição do MBA com provenance e `reason_retrieved`;
8. usuário B recebe zero resultados;
9. revogação de `chatgpt-sim` bloqueia novas chamadas;
10. `claude-sim` continua funcionando dentro de seus scopes;
11. forget remove a memória e restore não a ressuscita.

### Pacote Codex M1-A — domínio de captura

**Modelo:** Terra.

Entregar:

- `source_client`, conversation/message IDs opcionais e captured_at;
- consent/capture mode;
- novos states candidate/confirmed/pinned/stale;
- `mental_note`;
- spaces e política cross-space;
- compatibilidade de migration com v0;
- commands/application services;
- testes de lifecycle, conflito e idempotência.

Gate: domínio e migrations verdes sem quebrar v0.

### Pacote Codex M1-B — tools e conformance

**Modelo:** Terra.

Entregar:

- `memory.capture`;
- review/confirm/pin ou composição equivalente;
- recall com filtros de espaço;
- provenance seguro;
- scopes e annotations;
- conformance cross-client simulado.

Gate: cenário obrigatório completo por HTTP MCP.

### Pacote Codex M1-C — Memory Inbox local

**Modelo:** Luna.

Entregar:

- `/memory-inbox`;
- origem e razão da sugestão;
- confirmar/editar/descartar;
- “nunca registrar esta categoria”;
- política por conexão;
- teste browser E2E conectado ao Admin API local.

Gate: ação na UI altera recall real no segundo cliente simulado.

## 7. M2 — Identity & Hosted Alpha

### Objetivo

Trocar adapters locais por serviços reais em staging, mantendo interfaces e
testes locais.

### Decisões humanas antes do goal

- IdP/e-mail selecionado;
- provedor de Postgres;
- KMS/secret manager;
- hosting do gateway/worker/web;
- domínio de staging;
- orçamento e região de dados.

### Pacote Codex M2-A — provider spike

**Modelo:** Terra.

- comparar no máximo dois candidatos por decisão;
- provar Google login, magic link, OIDC/JWKS e OAuth MCP;
- provar local dev, exportabilidade, revogação e custos;
- registrar ADR com escolha e fallback;
- não provisionar produção sem autorização.

### Pacote Codex M2-B — auth e consentimento

**Modelos:** Terra backend; Luna UI.

- `/oauth/authorize`;
- Continue with Google;
- magic link;
- PKCE;
- resource indicators/audience;
- scopes por conexão;
- consent screen;
- callback allowlist;
- token rotation/revocation;
- session security;
- anti-enumeration e abuse controls.

### Pacote Codex M2-C — tenancy staging

**Modelo:** Terra.

- FORCE RLS;
- roles separadas;
- tenant context;
- KMS real;
- encrypted backups;
- tombstone restore;
- redacted observability;
- load baseline.

### Gate M2

- conta Google/e-mail em staging;
- duas conexões ligadas à mesma identidade;
- tokens revogados falham;
- testes cross-tenant adversariais;
- dump/backup claims verificados;
- privacy/threat model atualizados;
- nenhum segredo em repo/logs.

## 8. M3 — Cross-client Connectors

### Objetivo

Provar portabilidade em superfícies reais sem anunciar universalidade.

### Ordem

1. agente Python controlado pelo projeto;
2. ChatGPT developer mode;
3. Claude API ou cliente documentado;
4. Gemini CLI;
5. agente TypeScript;
6. superfícies adicionais apenas após contrato verde.

### Pacote Codex por conector

Cada goal entrega:

- receita versionada;
- fluxo de auth;
- write/capture;
- recall;
- update/forget;
- revogação;
- prompts positivos/indiretos/negativos;
- limitações;
- relatório datado e checksummed;
- linha atualizada na compatibility matrix.

### Gate M3

- pelo menos dois clientes reais diferentes completam o cenário M1;
- um registra e o outro recupera;
- provenance identifica o cliente de origem;
- client sem autorização recebe erro seguro;
- matriz diferencia Supported, Experimental e Unverified.

## 9. M4 — Memory Atlas

### Objetivo

Tornar a memória visível e útil fora do momento de chat.

### Pacote Codex M4-A — concepts domain

**Modelo:** Terra.

- `concepts`;
- `memory_concepts`;
- concept relationships;
- resumo versionado;
- salience;
- provenance;
- jobs de recalculação idempotentes;
- invalidação após update/forget;
- APIs paginadas.

### Pacote Codex M4-B — Concepts UI

**Modelo:** Luna.

- `/concepts`;
- `/concepts/:id`;
- lista, busca e filtros;
- resumo e memórias de suporte;
- relações em lista acessível;
- grafo progressivo opcional;
- evolução e perguntas abertas;
- why/provenance.

### Pacote Codex M4-C — Mental Notes

**Modelos:** Terra + Luna.

- `/notes`;
- pin/unpin;
- nota direta;
- objetivos, decisões e open questions;
- mover de espaço;
- relacionar conceitos;
- resolver/arquivar/forget;
- ordenação por importância e retorno sugerido.

### Pacote Codex M4-D — Activity

- recibos audit-safe;
- captura/recall/update/delete/revoke;
- filtros por conexão e espaço;
- “why recalled?”;
- sem chain-of-thought e sem payload em telemetry.

### Gate M4

- conceitos sempre rastreáveis a memórias;
- forget invalida resumos/arestas;
- UI completa por teclado e mobile;
- usuário consegue corrigir uma inferência;
- nenhuma visualização fabrica dados quando backend falha.

## 10. M5 — Trusted Recall

### Objetivo

O sistema lembra o que ajuda, abstém quando deve e não surpreende o usuário.

### Workstreams

- corpus development multilíngue separado;
- eval de capture precision;
- eval de deduplicação e conflito;
- eval de cross-space relevance;
- eval de provenance;
- prompt-injection e memory poisoning;
- outdated-memory handling;
- concept consolidation;
- latency/cost/queue budgets;
- policy engine manual/assisted/automatic.

### Métricas mínimas

- precision@k e intrusion por slice;
- abstention;
- useful recall rate;
- wrong-memory confirmation rate;
- candidate accept/edit/reject rate;
- stale/contradiction detection;
- latency p50/p95/p99;
- cross-tenant leakage zero;
- category-policy violation zero.

### Gate M5

- thresholds pré-registrados;
- development e holdout separados;
- holdout apenas após autorização e SHA congelado;
- falha não é corrigida baixando meta retroativamente;
- claim de idioma limitada ao corpus comprovado.

## 11. M6 — Private Managed Beta

### Objetivo

Validar valor e operação com 5–20 usuários consentidos, sem publicar código,
artefatos, SDKs ou promessas de compatibilidade.

### Pacotes Codex

- onboarding e suporte;
- feature flags e quotas;
- analytics opt-in agregada;
- admin operational console sem leitura casual de conteúdo;
- incident drills;
- restore/delete drills;
- cost dashboards;
- feedback de recall e captura;
- export/delete account;
- privacy/support/security pages;
- beta release notes.

### Gate M6

- nenhum P0/P1 aberto;
- SLO observado;
- restore comprovado;
- deleção comprovada;
- usuários compreendem captura e controle;
- incident channel e security reporting ativos;
- rollback ensaiado.

## 12. M7 — Open-source Release

### Objetivo

Publicar UMCP Community de modo reproduzível e seguro, após o beta privado ter
sido operado e auditado. M7 não é pré-requisito para convidar o cohort M6.

### Pacotes Codex

- quickstart limpo;
- Docker multi-arch;
- wheel/sdist;
- sample agents;
- self-hosted auth options;
- migrations empacotadas;
- docs de upgrade/rollback;
- license/governance/DCO;
- CODEOWNERS e templates;
- required CI;
- secret/dependency/license scans;
- SBOM;
- provenance/signing;
- vulnerability reporting;
- changelog e semantic versioning.

### Gate M7

- build de SHA limpo;
- instalação limpa nas plataformas declaradas;
- artifacts checksummed/assinados;
- branch protection e CI remotos comprovados;
- auditoria S07-R2 independente `GO`;
- publicação autorizada separadamente.

## 13. M8 — Public Beta e GA

### Public Beta

- onboarding self-service;
- conectores anunciados comprovados;
- quotas/custos/suporte;
- status page;
- privacy e subprocessors;
- monitoring e alertas;
- feedback loops;
- capacidade e abuse testing.

### GA

- SLO sustentado;
- auditoria de auth/RLS/crypto;
- threat model revisado;
- holdout `GO` no SHA candidato;
- backup/restore/delete em produção comprovados;
- incident drills;
- claims aprovadas;
- compatibilidade datada;
- autorização humana explícita de lançamento.

## 14. Backlog de epics

| ID | Epic | Marco | Owner preferido |
| --- | --- | --- | --- |
| MEM-01 | Source metadata e provenance | M1 | Terra |
| MEM-02 | Capture modes e policies | M1/M5 | Terra |
| MEM-03 | Spaces e cross-space recall | M1 | Terra |
| MEM-04 | Memory Inbox | M1 | Luna |
| ID-01 | Google/email identity | M2 | Terra/Luna |
| ID-02 | MCP OAuth consent | M2 | Terra |
| TEN-01 | RLS multitenancy | M0/M2 | Terra |
| CRY-01 | Envelope encryption/KMS | M0/M2 | Terra |
| CON-01 | ChatGPT integration | M3 | Luna |
| CON-02 | Claude integration | M3 | Luna |
| CON-03 | Gemini CLI integration | M3 | Luna |
| SDK-01 | Python/TS agents | M1/M3 | Luna |
| ATL-01 | Concepts domain | M4 | Terra |
| ATL-02 | Concepts UI | M4 | Luna |
| ATL-03 | Mental Notes | M4 | Terra/Luna |
| ATL-04 | Activity/why recalled | M4 | Terra/Luna |
| EVAL-01 | Capture/retrieval quality | M5 | Terra |
| OPS-01 | Backup/restore/delete | M0/M6 | Terra |
| OSS-01 | Community release | M7 | Terra/Luna |
| AUD-01 | Independent release audit | M7/M8 | auditor |

## 15. Sequência recomendada de goals

1. `G00` — auditar Integration Recovery e incorporar as lições do pós-mortem.
2. `G01` — fechar findings M0.
3. `G02` — domínio de captura, spaces e provenance.
4. `G03` — tools de captura/recall e conformance cross-client simulado.
5. `G04` — Memory Inbox integrada.
6. `G05` — spike e ADR de providers hosted.
7. `G06` — auth/consent/RLS/KMS em staging.
8. `G07` — conector ChatGPT comprovado.
9. `G08` — conector Claude comprovado.
10. `G09` — conector Gemini CLI e agentes próprios.
11. `G10` — concepts domain e workers.
12. `G11` — Memory Atlas/Concepts UI.
13. `G12` — Mental Notes e Activity.
14. `G13` — trusted recall evals e hardening.
15. `G14` — closed beta readiness.
16. `G15` — open-source RC.
17. `G16` — auditoria independente.
18. `G17` — publicação autorizada.

Cada goal só começa depois de ler o handoff do anterior. Goals independentes de
frontend/backend podem usar worktrees paralelas após contrato congelado.

### Requisitos adicionais de G00

- localizar o HEAD final de `product/integration`;
- comparar o estado final com o pós-mortem e `INTEGRATION-RC.md`;
- repetir gates que o pós-mortem classifica como históricas;
- validar worktree/branch/SHA;
- executar ou criar uma demo local única;
- não contar browser E2E como verde sem execução real;
- classificar adapters locais versus produção;
- criar a primeira tabela de gate freshness;
- fechar findings antes de iniciar M1.

## 16. Template de prompt autônomo

```text
/goal

Objetivo: executar o pacote <ID/NOME> do
docs/CODEX_DELIVERY_ROADMAP.md e satisfazer integralmente seu gate.

Leia primeiro:
- docs/PRODUCT_VISION_PORTABLE_MEMORY.md
- docs/CODEX_DELIVERY_ROADMAP.md
- docs/GAMEPLAN_PRODUCTIZATION_TERRA_LUNA.md
- docs/EXECUTION_RELIABILITY_PLAYBOOK.md
- ADRs e handoff do marco anterior.

Implemente, teste, corrija, documente e crie commits locais. Não entregue apenas
um plano. Não pare na primeira falha. Use adapters locais para dependências
externas ausentes e conclua todo trabalho independente.

Mantenha WIP limit de um marco. Antes de implementar, congele acceptance test e
demo. Antes de avançar, execute gates no HEAD, classifique freshness e produza
handoff. Se o detector de estagnação disparar, reduza o problema e mude de
estratégia conforme o playbook, em vez de acumular patches.

Autorizado localmente: edição, dependências open source, Docker descartável,
migrations descartáveis, testes, builds, scanners, worktree/branch e commits
locais.

Não autorizado: holdout, push, PR, tag, release, deploy, serviços pagos, e-mail
real, dados reais ou uso de segredo comprometido.

Produza docs/handoffs/productization/<ID>-DONE.md com SHA, paths, comandos,
resultados, skips, claims, riscos e próximos gates. Só marque concluído quando o
gate do pacote estiver satisfeito ou todo trabalho independente estiver completo
e um bloqueio externo real estiver demonstrado.
```

## 17. Decisões que continuam humanas

Codex pode pesquisar, comparar, implementar e testar, mas o mantenedor aprova:

- provedor e orçamento de hosting/IdP/KMS/e-mail;
- região e política de dados;
- domínio e marca final;
- execução do holdout;
- usuários do beta;
- termos/privacy finais e aconselhamento jurídico;
- publicação, push, release e GA;
- aceitação explícita de riscos residuais.

## 18. Definition of Done do roadmap

O roadmap está entregue quando:

- a história cross-assistant funciona em clientes reais anunciados;
- tenant isolation e revogação são comprovados;
- Memory Inbox, Concepts e Mental Notes são utilizáveis;
- captura é consentida e minimizada;
- recall possui provenance e explicação;
- o usuário pode exportar e esquecer;
- restore não ressuscita conteúdo esquecido;
- Community pode ser instalada de release reproduzível;
- Cloud sustenta SLO e operação de beta/GA;
- claims públicas correspondem à evidência;
- auditoria independente registra `GO` no SHA publicado.
