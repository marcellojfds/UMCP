# UMCP — gameplan de produtização com Terra + Luna

**Documento:** plano executivo de produto, arquitetura, segurança, open source e lançamento
**Data-base:** 2026-08-21
**Marca de trabalho:** **UMCP — Open Memory Protocol**
**Estado inicial:** Alpha local/self-hosted; não é um release público nem um serviço multiusuário
**Regra de conclusão:** nenhum executor pode converter evidência parcial em `GO`

---

## 1. Resultado pretendido

Transformar o núcleo atual em uma plataforma de memória de longo prazo que seja:

1. independente do provedor de modelo;
2. utilizável por ChatGPT, Claude, Gemini em superfícies comprovadamente compatíveis e agentes próprios;
3. oferecida em duas formas: open source/self-hosted e serviço hospedado;
4. multiusuário, com identidade derivada do login e nunca de um `owner_id` confiado ao cliente;
5. segura para dados pessoais, com controles criptográficos e alegações públicas estritamente verificadas;
6. simples de instalar, conectar, entender, inspecionar, corrigir, exportar e apagar;
7. observável, recuperável e publicável a partir de um SHA imutável.

### Tese de produto

> **Your memory should outlive the model.**

Subtítulo sugerido:

> **One memory layer for ChatGPT, Claude, Gemini and your own agents.**

O produto não deve ser vendido como “histórico de conversa” nem como um dump de RAG. Ele é uma camada estruturada e controlável de memória: o assistente recupera contexto relevante, registra algo quando permitido e o usuário pode revisar, corrigir, exportar ou esquecer.

### Entregáveis de saída

- `umcp-core`: núcleo Python open source, mantendo compatibilidade com o pacote atual.
- MCP local via `stdio` para self-hosting e desenvolvimento.
- MCP remoto via Streamable HTTP em endpoint HTTPS estável, normalmente `/mcp`.
- identidade, autorização, consentimento, quotas e isolamento multi-tenant.
- landing page, autenticação por e-mail e painel do usuário.
- fluxo guiado de conexão por cliente, com matriz de compatibilidade pública.
- SDKs mínimos Python e TypeScript para agentes próprios.
- implantação de staging, observabilidade, backup/restore e operação de deleções.
- cadeia de release open source: CI, SBOM, artefatos assinados, documentação e auditoria.
- beta fechado validado e critérios objetivos de GA.

---

## 2. Verdade inicial e limites que não podem ser apagados

### 2.1 Estado técnico atual

- O projeto é `0.1.0a1`, Python 3.11, PostgreSQL 16 + pgvector.
- O MCP atual usa somente `stdio` e expõe quatro ferramentas: `memory.write`, `memory.search`, `memory.update` e `memory.forget`.
- `owner_id` é fornecido e confiado pelo cliente. Isso é apenas separação lógica em ambiente local confiável; não é autenticação nem autorização.
- Conteúdo, provenance e embeddings são legíveis pelo operador do banco/processo.
- Não há E2EE, zero knowledge, hospedagem multiusuário ou endpoint MCP HTTP de produção.
- O candidato E5 congelado está **development promotion eligible**, não `GO` de release.
- A última evidência de development registra `precision@5=0.899`, intrusion `0`, abstention `1`, IDs equivalentes e scores dentro de `1e-6` entre harness e PostgreSQL/gateway.
- O holdout continua fechado. Ele não pode ser executado ou inspecionado sem autorização separada.
- A árvore Git contém trabalho local tracked e untracked. O manifesto T04 propõe commits, mas não autoriza stage, commit, push ou ação remota.
- CI remoto, proteção de branch/PVR e uma auditoria S07-R2 independente ainda não existem como evidência de `GO`.

### 2.2 Regras invioláveis

- Preservar todo o trabalho local e seus checksums antes de qualquer reorganização.
- Não reexecutar development para escolher retroativamente modelo ou threshold.
- Não abrir, medir, ajustar ou selecionar com o holdout antes da autorização e do SHA candidato congelado.
- Não executar `git add`, commit, push, PR, tag, release ou alteração de GitHub sem a autorização correspondente.
- Não usar a chave OpenAI publicada na conversa. Ela deve ser revogada e substituída.
- Nunca armazenar segredos em Git, documentação, artifacts, logs, screenshots, comandos persistidos ou fixtures.
- Não anunciar “tudo criptografado”, E2EE, zero knowledge, suporte universal ou compliance sem evidência que corresponda literalmente à alegação.
- Uma falha P0 de isolamento, autenticação, deleção, recuperação ou vazamento impede lançamento.

### 2.3 Autorizações separadas

Cada item abaixo é uma decisão própria; autorizar um não autoriza os demais:

1. rotação e configuração local de novos segredos;
2. instalação/download de dependências e ferramentas de auditoria;
3. stage de paths exatos;
4. criação de commits locais;
5. push/branch/PR e alterações em settings do GitHub;
6. aquisição de infraestrutura ou serviço pago;
7. execução única do holdout congelado;
8. publicação de site, imagem, pacote, container, tag ou release;
9. envio de e-mails reais;
10. abertura de beta para usuários externos.

---

## 3. Decisões de produto e arquitetura a congelar primeiro

Terra redige as ADRs; Luna valida impacto em onboarding, documentação e UX. Nenhuma implementação estrutural começa antes de as ADRs 0009–0015 estarem aceitas localmente.

### ADR 0009 — produto em duas edições

**Recomendação:** um único core e duas composições.

| Edição | Público | Transporte | Identidade | Armazenamento |
| --- | --- | --- | --- | --- |
| UMCP Community | desenvolvedor/usuário técnico | stdio e HTTP opcional | operador local/PAT opcional | PostgreSQL próprio |
| UMCP Cloud | usuário final/equipes/agentes | Streamable HTTP HTTPS | e-mail + OAuth/OIDC | PostgreSQL gerenciado multi-tenant |

Não criar duas implementações do domínio. Adapters diferentes devem usar os mesmos application services e contratos.

### ADR 0010 — transporte MCP e API administrativa

- Manter `stdio` como caminho local.
- Adicionar Streamable HTTP no SDK oficial MCP, montado em ASGI.
- Reservar `/mcp` exclusivamente para protocolo MCP.
- Expor health/readiness sem dados sensíveis.
- Usar API web administrativa separada para dashboard, conexões, export e configurações.
- Não implementar business logic duplicada em REST.
- Manter SSE apenas se uma integração comprovadamente exigir compatibilidade legada.
- Definir versionamento do contrato, deprecação e conformance tests.

### ADR 0011 — identidade e autorização

**Regra principal:** em hosted, a identidade vem do token verificado; o cliente não escolhe o proprietário.

- autenticação do site por e-mail, preferencialmente magic link ou OTP;
- sessões web seguras em cookies `HttpOnly`, `Secure`, `SameSite` adequado;
- OAuth 2.1/OIDC para clientes MCP, PKCE obrigatório para clientes públicos;
- metadata do authorization server e protected resource;
- scopes mínimos: `memory:read`, `memory:write`, `memory:delete`, `memory:export`, `connections:manage`;
- tokens curtos, refresh rotation, revogação e audiência/resource binding;
- PAT/service-account apenas para agentes e automações, com hash no banco, expiração, scopes e exibição única;
- consentimento explícito por integração;
- principal resolvido no gateway e injetado no serviço;
- `owner_id` é removido dos schemas hosted ou ignorado/rejeitado; permanece somente no modo local compatível.

O provedor de identidade não será construído do zero. Terra executará um spike time-boxed comparando no máximo dois fornecedores que comprovem: e-mail passwordless, OIDC/JWKS, hooks ou claims, exportabilidade, ambiente local, política de privacidade, custo previsível e possibilidade de suportar o fluxo MCP. A escolha precisa de ADR e teste, não de preferência estética.

### ADR 0012 — multi-tenancy

**Recomendação v1:** banco compartilhado com RLS default-deny, chaves compostas e contexto transacional obrigatório; banco dedicado fica como opção enterprise futura.

Entidades mínimas:

- `users`;
- `workspaces` ou `tenants`;
- `memberships` e roles;
- `identities`;
- `oauth_clients`/`connections`;
- `agent_credentials`;
- `consents`;
- `memories`, versions, relations e embeddings com `tenant_id`;
- `audit_events` sem payload de memória;
- `deletion_tombstones` duráveis;
- `usage_counters` e quotas.

Controles:

- RLS habilitado e forçado nas tabelas de usuário;
- política default-deny;
- `tenant_id` derivado da sessão/token e aplicado em transação;
- FKs e índices compostos incluindo `tenant_id` onde necessário;
- testes adversariais cross-tenant em todas as operações e jobs;
- nenhuma consulta de aplicação sem tenant context;
- workers recebem identidade/tenant autenticados em envelope assinado;
- logs, traces e métricas nunca recebem conteúdo, query bruta, e-mail ou token.

### ADR 0013 — criptografia e alegações públicas

O design prático de v1 será **server-decryptable**, porque o servidor precisa processar texto e vetores para retrieval. Portanto:

- TLS em trânsito entre cliente, gateway, banco, filas e provedores;
- criptografia de volume/banco e backups em repouso;
- envelope encryption application-layer para conteúdo e provenance, usando DEK por tenant e KEK em KMS/HSM;
- chave versionada, rotação, rewrap e revogação testados;
- secretos somente em secret manager;
- vetores classificados como sensíveis; enquanto precisarem de indexação pgvector, ficam protegidos por criptografia em repouso, RLS e controle de acesso, não por E2EE;
- metadata minimizada e pseudonimizada quando possível;
- audit trail para acesso administrativo e operações de chave;
- break-glass com justificativa, tempo limitado e alerta;
- exports criptografáveis e download temporário;
- backups criptografados, inventariados e submetidos à política de deleção.

**Claim gate:**

| Alegação | Quando pode aparecer |
| --- | --- |
| “Encrypted in transit and at rest” | somente após TLS e storage/backups verificados em staging |
| “Memory content is encrypted with per-tenant keys” | após ciphertext-at-rest, rotação e restore testados |
| “Your memory is user-controlled” | após inspect/edit/export/delete/revoke funcionarem E2E |
| “End-to-end encrypted” | proibido no v1 server-decryptable |
| “Zero knowledge” | proibido sem arquitetura e auditoria próprias |
| “Everything is encrypted” | não usar; é impreciso para metadata e vetores indexáveis |

Uma trilha futura pode estudar embeddings locais, confidential compute ou índices privados. Ela não bloqueia o beta e não pode contaminar as alegações do v1.

### ADR 0014 — retrieval e idiomas

- preservar E5 congelado e threshold `0.76` até o gate formal;
- manter `hash/v1` como fallback compatível, sem alegá-lo como retrieval semanticamente aprovado;
- bloquear mistura silenciosa de dimension/profile/version;
- jobs de re-embedding idempotentes, observáveis, retomáveis e tenant-scoped;
- registrar versão do modelo e da memória em cada vetor;
- não afirmar suporte multilíngue amplo apenas porque o protocolo aceita Unicode;
- criar corpus development separado para português/inglês e outros idiomas-alvo;
- novo candidato multilíngue exige ADR, dados pré-registrados e seu próprio holdout, sem alterar o candidato E5 histórico.

### ADR 0015 — marca e compatibilidade

- marca pública: **UMCP**;
- descritor: **Open Memory Protocol**;
- manter namespace Python `omp` e contratos v0 durante a primeira produtização para evitar um rename destrutivo;
- redirecionar nomes gradualmente por aliases e deprecation policy;
- pesquisar disponibilidade de domínio, GitHub, package registry e marca antes de prometer exclusividade;
- não inventar uma expansão retroativa para a letra “U” sem decisão do mantenedor;
- compatibilidade é declarada por superfície e versão, nunca por logotipo genérico.

---

## 4. Arquitetura-alvo

```text
 ChatGPT        Claude/API       Gemini CLI/API       Personal agents
    |               |                  |                    |
    +---------------+------------------+--------------------+
                            HTTPS / MCP
                                 |
                      +----------v-----------+
                      | UMCP MCP Gateway     |
                      | OAuth, scopes, quota |
                      | schema, consent      |
                      +----------+-----------+
                                 |
                      authenticated principal
                                 |
             +-------------------+-------------------+
             |                                       |
     +-------v---------+                     +-------v---------+
     | UMCP Core       |                     | Async workers   |
     | lifecycle       |                     | embed/re-embed  |
     | retrieval       |                     | consolidate     |
     | export/forget   |                     | deletion jobs   |
     +-------+---------+                     +-------+---------+
             |                                       |
             +-------------------+-------------------+
                                 |
                      +----------v-----------+
                      | PostgreSQL + pgvector|
                      | RLS + encrypted data |
                      +----------+-----------+
                                 |
                    KMS / backups / audit sink

 Browser -> Landing/Auth/Dashboard -> Web API -> same principal/core
```

### Limites de confiança

1. **Cliente:** não confiável; pode enviar argumentos maliciosos e prompt injection.
2. **Gateway:** valida token, scopes, schemas, rate limits e consentimento.
3. **Core:** não conhece segredos do cliente e recebe um principal já verificado.
4. **Worker:** processa somente jobs assinados/tenant-scoped.
5. **Database:** defesa em profundidade com RLS e constraints; não confiar apenas no ORM.
6. **Operador:** acesso privilegiado é possível no v1; precisa ser reduzido, auditado e descrito honestamente.

### Layout de repositório recomendado

Evoluir sem reescrever o core:

```text
src/omp/                    # core Python e adapters atuais
services/gateway/           # composição HTTP/OAuth/ASGI
services/worker/            # jobs assíncronos Python
apps/web/                   # landing, auth e dashboard
packages/sdk-python/        # cliente/integrações de agentes
packages/sdk-typescript/    # cliente/integrações de agentes
deploy/                     # compose, IaC, manifests, runbooks
docs/site/                  # documentação pública
docs/adr/                   # decisões
evals/                      # datasets/configs/reports governados
```

Antes de mover o package atual, construir adapters e extrair contratos. Evitar “big-bang monorepo rewrite”.

---

## 5. Compatibilidade: o que “todos os chats” significa na prática

O endpoint remoto comum é MCP Streamable HTTP, mas disponibilidade e onboarding variam por produto. Luna mantém uma matriz versionada com data do teste.

| Superfície | Integração-alvo | Status inicial permitido |
| --- | --- | --- |
| ChatGPT developer mode | endpoint público `/mcp` ou Secure MCP Tunnel para teste | validar E2E; túnel não é distribuição pública |
| ChatGPT plugin/app publicado | endpoint HTTPS estável, auth discovery e revisão | bloqueado até requirements e publicação aprovados |
| OpenAI Responses API/agentes | MCP remoto autenticado | validar com exemplo automatizado |
| Claude API | MCP connector remoto com bearer/OAuth conforme suporte atual | validar tools, scopes e erros |
| Claude Desktop/Code | stdio local e/ou remote conforme cliente | validar configs e versões específicas |
| Gemini CLI | `mcpServers` local ou `httpUrl` remoto | validar config, refresh e tool calls |
| Gemini API/ADK | adapter MCP oficial quando disponível | spike e teste oficial |
| Gemini consumer web/mobile | não prometer sem mecanismo oficial verificado | “not currently verified” |
| agentes próprios | SDK Python/TS + MCP remoto/PAT | suportado após conformance suite |
| qualquer outro cliente MCP | protocolo padrão | “compatible”, não “tested”, até evidência |

Cada linha deve publicar:

- superfície e versão/data;
- transporte;
- método de autenticação;
- leitura/escrita/delete suportados;
- confirmação de ação destrutiva;
- limitações conhecidas;
- link para receita testada;
- ID do relatório de compatibilidade.

Não usar um badge “Works everywhere” antes de todas as linhas relevantes estarem verdes.

---

## 6. Experiência do produto

### 6.1 Landing page

Referência visual: adaptar a linguagem editorial de `fathom-context.marcellojfds.chatgpt.site`, sem copiar texto, identidade ou composição literalmente.

Tokens de direção visual:

- fundo papel quente próximo de `#f3f1eb`;
- tinta carvão próxima de `#363735`;
- divisórias cinza suave;
- laranja vivo próximo de `#ff4f28` como único acento principal;
- títulos geométricos densos;
- frases-chave em serif itálica;
- labels e metadados em mono;
- muito espaço negativo, linhas finas e movimento orbital contido;
- contraste WCAG AA, navegação por teclado e reduced-motion.

Estrutura:

1. **Hero:** “Your memory should outlive the model.”
2. **Proposição:** uma camada de memória para vários assistentes.
3. **Problema:** contexto fragmentado, repetição e lock-in.
4. **Como funciona:** Remember → Retrieve → Correct → Forget.
5. **Diagrama de ecossistema:** clientes orbitando um núcleo UMCP.
6. **Exemplo visual:** a mesma preferência recuperada com permissão em dois assistentes.
7. **Controle:** inspecionar, editar, exportar, apagar e revogar.
8. **Segurança:** claims exatos, limites e link para threat model.
9. **Open source:** GitHub, self-hosting, licença Apache-2.0 e contribuição.
10. **Compatibilidade:** matriz real, sem logos que impliquem parceria.
11. **FAQ:** o que é lembrado, quando escreve, onde ficam os dados, como apagar, diferença para histórico.
12. **CTA:** criar conta ou self-host.

Diagramas devem ser HTML/CSS/Canvas acessíveis e responsivos, com explicação textual equivalente. Evitar SVG complexo gerado automaticamente e evitar screenshots falsos do produto.

### 6.2 Auth por e-mail

Rota mínima: `/login` e callback verificado.

Layout:

- painel editorial à esquerda com a tese e diagrama de memória;
- cartão limpo à direita com e-mail, submit, estado de envio, reenvio e troca de endereço;
- magic link/OTP com expiração curta;
- mensagens anti-enumeration: não revelar se o e-mail existe;
- rate limit por IP/e-mail e proteção contra abuso;
- termos, privacidade, suporte e consentimento;
- sessão criada apenas no servidor;
- redirect pós-login validado contra allowlist;
- nenhum token em analytics ou URL persistida;
- estados mobile, loading, offline, expirado e erro testados.

Antes de implementar a tela final em Sites, confirmar que o caminho de autenticação público escolhido pode ser integrado no runtime atual. “Sign in with ChatGPT” não substitui autenticação por e-mail para usuários externos e multicliente.

### 6.3 Dashboard

Rotas mínimas:

- `/dashboard`: estado, uso, últimos eventos sem payload;
- `/memories`: busca, filtros, inspeção e paginação;
- `/memories/:id`: conteúdo, provenance, versões e relações permitidas;
- `/connections`: conectar/revogar clientes e mostrar scopes;
- `/agents`: criar/revogar credenciais de agentes;
- `/settings/security`: sessões, chaves, export, delete account;
- `/docs`: instalação e receitas por cliente;
- `/status`: status operacional sem dados de tenant.

Operações destrutivas exigem confirmação clara, reautenticação quando aplicável, idempotency key e feedback auditável.

### 6.4 Fluxo de memória

Para evitar que qualquer modelo encha a base com lixo:

- `memory.search` é read-only e pode ser usado automaticamente conforme consentimento;
- `memory.write` explicita categoria, provenance, confiança e motivo;
- preferências do usuário definem auto-capture desligado/assistido/permitido;
- conteúdo vindo de memória é tratado como dado não confiável, nunca como instrução de sistema;
- conflitos criam nova versão ou pedem confirmação, não sobrescrevem silenciosamente;
- `forget` possui preview do impacto e confirmação onde o cliente suporta;
- UI permite corrigir e marcar memória como pinned/archived/invalid;
- consolidação não perde provenance nem torna fato uma hipótese.

---

## 7. Plano por ondas

## Onda 0 — contenção, baseline e autorização

**Owner:** Terra
**Luna:** somente leitura/revisão
**Paralelo:** não

### Tarefas

- revogar a chave OpenAI exposta e qualquer chave derivada dela;
- procurar apenas padrões/redações de segredo no workspace e histórico local disponível, sem imprimir valores completos;
- produzir inventário da árvore atual e checksums dos artifacts;
- reconciliar `GOAL-PROGRESS`, S07 histórico, T03 atual e T04, preservando cronologia;
- executar gates locais não destrutivos já suportados;
- validar que modelo/cache/venv/dumps não entram no manifesto;
- obter autorização para stage/commits exatos do T04;
- criar os quatro commits propostos, se e somente se autorizados;
- registrar SHA baseline limpo;
- criar worktrees/branches separadas para Terra e Luna, se autorizado;
- definir diretórios de propriedade e contrato de handoff.

### Saída

- `P00-baseline-manifest.md`;
- `P00-secret-rotation.md` sem segredos;
- SHA limpo ou bloqueio explícito;
- worktrees isoladas, nunca dois executores no mesmo checkout mutável.

### Gate P0

- nenhum segredo ativo conhecido exposto;
- checksums íntegros;
- `git status` limpo no baseline;
- gates locais verdes ou findings registrados;
- nenhuma alegação de release `GO`.

## Onda 1 — contratos e ADRs

**Owner:** Terra
**Luna:** compatibilidade, UX e revisão documental
**Paralelo:** controlado

### Tarefas Terra

- redigir ADRs 0009–0015;
- threat model hosted v1 com STRIDE/abuse cases;
- definir claims matrix;
- definir schema de principal, scopes e consentimento;
- definir contratos de gateway/core/worker;
- definir migrations multi-tenant e plano rollback/forward-fix;
- definir provider-decision spike para auth e infraestrutura.

### Tarefas Luna

- inventariar jornadas por ChatGPT, Claude, Gemini e agentes;
- produzir matriz de compatibilidade com links oficiais e data;
- wireframes textuais e design tokens;
- inventário de copy e claims dependentes de gate;
- especificar SDK examples e conformance fixtures.

### Gate P1

- contratos e schemas revisados;
- nenhum `owner_id` controlado pelo cliente em hosted;
- riscos de criptografia e vetores explicitados;
- UX não promete capability inexistente;
- plano de migration tem teste zero→head, upgrade e restore.

## Onda 2 — gateway remoto e identidade

**Owner:** Terra
**Luna:** fixtures de integração e documentação
**Paralelo:** sim, sobre contratos congelados

### Tarefas

- montar Streamable HTTP `/mcp` sem duplicar os application services;
- implementar initialize/list/call e streaming conforme SDK;
- health/readiness e graceful shutdown;
- validar issuer, assinatura, audience/resource, expiry, scopes e revogação;
- metadata OAuth/protected-resource;
- PKCE e callback allowlist;
- consentimento por client e scopes;
- PAT scoped para agentes, guardado somente como hash;
- rate limits e quotas;
- erros padronizados sem leak;
- annotations corretas para read/write/destructive/idempotent;
- manter stdio e provar paridade de resultado.

### Testes

- MCP Inspector;
- contract tests stdio vs HTTP;
- token ausente, inválido, expirado, issuer/audience errados;
- scope insuficiente;
- replay/idempotency;
- desconexão durante stream;
- payload/headers grandes;
- prompt/tool injection;
- brute force/rate limit;
- logs sem bearer, cookie, e-mail, conteúdo ou query.

### Gate P2

- endpoint funciona em staging HTTPS;
- auth discovery comprovada;
- zero caminho hosted aceita `owner_id` forjado;
- paridade funcional stdio/HTTP;
- compatibilidade ChatGPT em developer mode comprovada sem usar o túnel como arquitetura de produção.

## Onda 3 — dados multi-tenant e criptografia

**Owner:** Terra
**Luna:** dashboard fixtures e testes E2E de usuário
**Paralelo:** sim, após schemas publicados

### Tarefas

- criar users/tenants/memberships/connections/credentials/consents/audit/tombstones;
- adicionar `tenant_id` aos dados de memória de forma migrável;
- RLS default-deny e role separada para migration;
- contexto de tenant transacional fail-closed;
- envelope encryption versionada para campos de payload;
- integração KMS/secret manager por adapter;
- rotação e rewrap online;
- política de backup, restore, retention e deletion reapplication;
- export por usuário/tenant com URLs temporárias e criptografia opcional;
- account deletion assíncrona com estado e recibo;
- break-glass e auditoria administrativa;
- minimizar metadata e classificar embeddings.

### Testes obrigatórios

- consultas cross-tenant adversariais por cada repository e job;
- property tests de RLS e FKs compostas;
- dump do banco não revela campos declarados encrypted;
- troca de ciphertext/tenant falha autenticação criptográfica;
- rotação preserva leitura e bloqueia chave antiga conforme política;
- backup→restore→reaplicação de tombstones;
- export/forget concorrentes;
- deleção durante re-embedding;
- falha de KMS fail-closed, sem fallback plaintext;
- auditoria não contém payload.

### Gate P3

- nenhuma falha de isolamento em toda a matriz;
- restore e deleção demonstrados;
- claims criptográficos correspondem à evidência;
- threat model atualizado após implementação;
- revisão independente dos paths de auth/crypto/RLS.

## Onda 4 — retrieval, workers e qualidade

**Owner:** Terra
**Luna:** harness, relatórios e UX de estados
**Paralelo:** sim

### Tarefas

- extrair embedding/re-embedding para worker idempotente;
- fila com dedupe, retry limitado, DLQ e tenant context;
- backpressure e quota;
- estado `pending/ready/stale/failed` visível sem retornar vetor stale;
- versionar modelo/profile/dimension/source_version;
- circuit breaker e degradação documentada;
- métricas agregadas sem conteúdo;
- preservar candidato E5 congelado;
- adicionar suites de português/inglês sem tocar no holdout congelado;
- calibrar novos idiomas em protocolos separados;
- definir SLO e budgets a partir de staging, não de wishful thinking.

### SLOs iniciais propostos para beta

- disponibilidade mensal do data plane: `>=99.9%`;
- `memory.search` p95 do serviço `<=750 ms` em carga beta declarada;
- `memory.write` síncrono p95 `<=500 ms`, com embedding assíncrono quando configurado;
- erro 5xx `<0.5%` fora de incidentes declarados;
- RPO `<=24h` e RTO `<=4h` no beta, apertados após evidência;
- cross-tenant leakage: tolerância zero.

### Gate P4

- suites development verdes e reprodutíveis por SHA;
- mesma configuração no harness e gateway;
- worker suporta retry/restart sem duplicar ou cruzar tenants;
- holdout continua fechado até autorização específica;
- após clean SHA, CI verde e autorização, uma única execução do holdout produz decisão vinculada ao SHA;
- falha do holdout resulta em `NO-GO`, sem ajuste pós-hoc.

## Onda 5 — web, auth UI e dashboard

**Owner:** Luna
**Terra:** endpoints, authz e security review
**Paralelo:** sim, após ADR de auth

### Tarefas

- implementar landing com sistema visual aprovado;
- implementar login por e-mail e callbacks server-side;
- construir dashboard mínimo;
- conexão/revogação por cliente;
- memory explorer com paginação e estados vazios/erro;
- export/delete account;
- docs integradas;
- analytics somente consentido e sem dados de memória;
- SEO, metadata e social card apenas após identidade visual estabilizar;
- mobile-first, WCAG AA, keyboard e reduced motion;
- política de privacidade/termos/security em rotas públicas.

### Testes

- unit/component;
- Playwright E2E desktop/mobile;
- auth success/expired/replayed/abuse;
- tenant A nunca vê tenant B;
- CSRF, XSS, open redirect, session fixation;
- CSP e security headers;
- snapshots visuais e inspeção manual;
- performance budget: LCP, CLS, JS e imagens;
- link checker e copy/claim checker.

### Gate P5

- landing explica produto em menos de 30 segundos;
- auth funciona E2E com e-mail real em staging autorizado;
- dashboard permite controle real das memórias;
- nenhuma claim supera evidência;
- navegação e contraste acessíveis;
- mobile aprovado.

## Onda 6 — SDKs, receitas e conformance multicliente

**Owner:** Luna
**Terra:** correções de gateway e security
**Paralelo:** sim

### Entregáveis

- exemplo ChatGPT developer-mode por endpoint e, separadamente, túnel de teste;
- exemplo OpenAI Responses API;
- exemplo Claude API remoto;
- configs Claude Desktop/Code quando aplicável;
- exemplo Gemini CLI local/remoto;
- exemplo de agente Python;
- exemplo de agente TypeScript;
- coleção de prompts positivos, indiretos, negativos e destrutivos;
- conformance runner que lista tools, chama cada operação e valida erros/scopes;
- relatórios com versão/data por cliente.

### Gate P6

- cada integração “Supported” executa jornada write→search→update→forget;
- auth e revogação validadas;
- confirmação destrutiva validada onde suportada;
- superfícies não comprovadas aparecem como experimental/unverified;
- snippets partem de instalação limpa e não dependem do diretório home errado.

## Onda 7 — operação, supply chain e open source

**Owner:** Terra para operação; Luna para comunidade/docs
**Paralelo:** sim

### Operação

- IaC para staging e produção;
- imagens multi-arch mínimas, usuário não-root, read-only filesystem quando possível;
- migrations como job explícito;
- autoscaling e connection pooling;
- logs estruturados redacted, métricas e traces;
- alertas por SLO, fila, KMS, DB e auth;
- runbooks de incident, outage, compromise, key rotation, restore e deletion;
- synthetic probes no `/mcp` sem conteúdo real;
- custos e quotas observáveis por tenant;
- ambientes e chaves separados.

### Open source/release

- Apache-2.0 preservada;
- README orientado a tese, quickstart e limites;
- CONTRIBUTING, CODE_OF_CONDUCT e SECURITY revisados;
- governance, roadmap e RFC/ADR process;
- DCO e CODEOWNERS;
- issue/PR templates;
- semantic versioning e changelog;
- CI obrigatório: lint, types, unit, contract, PostgreSQL, MCP E2E, build, docs, secret scan, dependency audit;
- SBOM CycloneDX/SPDX;
- provenance/SLSA quando suportado;
- assinatura de containers/releases;
- Dependabot/Renovate e CodeQL/SAST;
- branch protection e PVR comprovados;
- wheel/sdist/container reconstruídos de SHA limpo;
- nenhum relatório sensível ou modelo pesado no Git.

### Gate P7

- instalação limpa por plataforma suportada;
- quickstart reproduzível;
- CI remoto verde e required checks ativos;
- artifacts vinculados ao SHA e checksummed;
- vulnerability policy cumprida;
- S07-R2 independente em `GO` antes de publicação.

## Onda 8 — beta fechado e GA

**Owners:** Terra + Luna
**Autorizações externas:** obrigatórias

### Beta fechado

- 5–20 usuários consentidos;
- dados sintéticos primeiro; dados pessoais somente após privacy gate;
- onboarding assistido e canal de suporte;
- métricas agregadas opt-in;
- feedback de relevância, controle, confiança e integração;
- incident drill e restore drill;
- orçamento/capacity test;
- rollback ensaiado.

### Critérios de GA

- todos os P0 e P1 fechados ou formalmente aceitos com owner/data;
- holdout `GO` no SHA candidato, sem ajuste pós-hoc;
- S07-R2 independente `GO`;
- CI remoto e branch protection verdes;
- compatibilidade comprovada nas superfícies anunciadas;
- auth, RLS e crypto auditados;
- backup/restore/delete comprovados;
- SLO observado no beta;
- docs, suporte, privacy e security channel ativos;
- autorização explícita de tag, release, site e abertura pública.

---

## 8. Divisão dos dois executores

## Executor Terra — autoridade do data plane

Propriedade primária:

- ADRs e arquitetura;
- `src/omp`, migrations, gateway e worker;
- authn/authz, tenancy, RLS, criptografia e KMS;
- PostgreSQL, filas, infra, observabilidade e runbooks;
- retrieval/re-embedding;
- gates de segurança, operação e release.

Terra não deve editar a landing e o design system salvo para corrigir integração ou segurança. Mudanças em contratos publicados exigem handoff para Luna.

## Executor Luna — autoridade da experiência e ecossistema

Propriedade primária:

- `apps/web`, docs públicas e design system;
- landing/auth/dashboard UI;
- copy e claim matrix refletida na interface;
- matriz de compatibilidade;
- SDKs, exemplos, onboarding e conformance fixtures;
- testes E2E web, acessibilidade, visual QA e documentação open source.

Luna não implementa uma segunda lógica de autorização nem acessa o banco diretamente do browser. Toda mutação usa APIs server-side autenticadas.

## Arquivos compartilhados

Somente mediante handoff:

- `pyproject.toml` e locks;
- schemas/contratos MCP;
- `.github/workflows`;
- `README.md`;
- `docs/adr`;
- migrations;
- manifests de deploy.

## Protocolo de handoff

Cada wave termina com `docs/handoffs/productization/<wave>-<agent>.md` contendo:

- SHA/base e branch;
- paths alterados;
- decisões e ADRs;
- comandos executados;
- resultados e artifacts/checksums;
- riscos/falhas/skips;
- migrations e rollback;
- claims habilitadas ou ainda proibidas;
- contrato que o outro executor pode consumir;
- ações que exigem autorização.

Nenhum executor faz merge direto do outro. Integração ocorre em checkpoint revisado, com diff e gates novamente executados.

---

## 9. Ordem prática de execução com dois `/goal`

### Passo 1 — iniciar apenas Terra

Terra executa Onda 0 até produzir baseline limpo ou bloqueio. Luna não deve começar mudanças antes do baseline/worktree.

### Passo 2 — abrir duas worktrees

Após autorização e baseline:

- `product/terra-data-plane`;
- `product/luna-experience`.

### Passo 3 — contratos em paralelo

Terra publica ADRs e schemas. Luna produz UX/compatibility specs sem depender da implementação.

### Passo 4 — waves 2–6

- Terra avança gateway → tenancy/crypto → workers.
- Luna avança design system → web → SDKs/conformance.
- checkpoint diário ou por contrato, nunca merge contínuo sem gate.

### Passo 5 — integração

- integrar primeiro contratos/gateway;
- depois web/auth;
- depois SDKs/compatibilidade;
- por fim infra/docs/release;
- rodar suite completa em um SHA limpo.

### Passo 6 — holdout e auditoria

- pedir autorização separada para holdout somente quando candidato e SHA estiverem congelados;
- executar uma vez e registrar resultado;
- abrir auditoria S07-R2 em sessão realmente independente;
- autores não podem autoatribuir `GO` final.

---

## 10. Prompt `/goal` para Terra

Copiar o bloco abaixo para o executor Terra:

```text
/goal
Objetivo: levar o UMCP — Open Memory Protocol do Alpha local ao data plane
hosted, multiusuário, seguro e release-ready, seguindo integralmente
docs/GAMEPLAN_PRODUCTIZATION_TERRA_LUNA.md. Você é o owner de arquitetura,
core Python, MCP gateway HTTP, identidade/autorização, PostgreSQL/RLS,
criptografia/KMS, workers, retrieval, infraestrutura, observabilidade e gates.

Comece pela Onda 0. Preserve a árvore atual e toda evidência. Leia T03, T04,
S07, privacy, threat model e os ADRs. Não execute holdout. Não faça stage,
commit, push, PR, tag, release, alteração remota, download, compra ou publicação
sem autorização explícita correspondente. A chave OpenAI exposta na conversa
é comprometida: não a use, não a imprima e não a grave; solicite/registre sua
revogação sem repetir o valor.

Primeiro produza um baseline verificável. Só depois, em worktree/branch própria,
redija e congele ADRs 0009–0015 e os contratos que Luna consumirá. Mantenha o
core único; adicione Streamable HTTP sem duplicar business logic; derive tenant
do token verificado; em hosted rejeite owner_id escolhido pelo cliente. Implemente
defesa em profundidade com OAuth 2.1/OIDC, scopes, consent, RLS default-deny,
constraints compostas, envelope encryption por tenant, secret manager, rotação,
backup/restore/tombstones, audit sem payload, rate limits e quotas.

Preserve stdio e prove paridade. Trate embeddings como dados sensíveis. Não
alegue E2EE, zero knowledge ou “everything encrypted”. O servidor v1 pode
descriptografar para retrieval, e isso deve ficar explícito. Falhas de KMS,
tenant context e auth devem ser fail-closed. Memórias recuperadas são dados não
confiáveis, nunca instruções.

Conduza as Ondas 0–4 e 7 do gameplan, respeitando gates. Produza handoff por
wave em docs/handoffs/productization. Rode testes proporcionais a cada mudança,
incluindo migrations zero→head, cross-tenant adversarial, ciphertext/rotation,
restore/delete, MCP Inspector, stdio/HTTP parity, retries de worker e scans.
Registre falhas e skips literalmente. Não ajuste modelo/threshold com holdout.

Coordene com Luna somente por contratos e handoffs. Não edite a experiência web
fora do necessário para integração/security. Ao encontrar mudanças no contrato,
publique primeiro schema/ADR e avise Luna. Só marque o goal concluído quando
todos os deliverables sob sua responsabilidade estiverem implementados e
verificados e nenhum trabalho seguro dentro do escopo restar. Mesmo então, não
declare release GO: holdout, CI remoto, autorização de publicação e S07-R2
independente continuam gates próprios.
```

## 11. Prompt `/goal` para Luna

Abrir somente após Terra concluir o checkpoint P0 e fornecer branch/worktree e contratos iniciais:

```text
/goal
Objetivo: transformar o UMCP — Open Memory Protocol em uma experiência pública
clara, confiável e instalável, seguindo integralmente
docs/GAMEPLAN_PRODUCTIZATION_TERRA_LUNA.md. Você é o owner de apps/web, landing,
auth UI, dashboard, docs públicas, matriz de compatibilidade, SDKs/exemplos,
onboarding e conformance/E2E do ecossistema.

Trabalhe apenas na worktree/branch designada após o checkpoint P0 de Terra.
Não mexa na árvore suja original. Não execute holdout. Não faça stage, commit,
push, PR, tag, release, alteração remota, download, compra, envio de e-mail real
ou publicação sem autorização explícita correspondente. Não use nem registre a
chave OpenAI exposta na conversa.

Use a estética editorial da referência Fathom como direção, não como cópia:
papel quente, tinta carvão, um acento laranja, títulos geométricos, serif itálica,
labels mono, linhas finas e movimento orbital contido. A marca é “UMCP” e o
descritor “Open Memory Protocol”. Construa uma landing simples com a tese
“Your memory should outlive the model”, exemplos visuais acessíveis e o fluxo
Remember → Retrieve → Correct → Forget. Implemente auth por e-mail conforme a
ADR de identidade de Terra e um dashboard real para memórias, conexões, agentes,
export, revogação e delete.

Não implemente autenticação fake ou somente client-side. Não consulte o banco
diretamente do browser. Não duplique authorization logic; consuma os endpoints
e schemas publicados por Terra. Não escreva “everything encrypted”, E2EE,
zero knowledge, works everywhere ou parceria com provedores. Use a claim matrix:
“encrypted in transit and at rest” e “per-tenant keys” só aparecem depois dos
gates correspondentes. Explique que o servidor v1 processa/decriptografa dados
para retrieval quando isso for verdade.

Mantenha uma matriz por superfície e data: ChatGPT developer mode/public app,
OpenAI API, Claude API/Desktop/Code, Gemini CLI/API e agentes próprios. Só marque
Supported após uma jornada write→search→update→forget autenticada. Gemini
consumer web/mobile fica unverified até existir caminho oficial comprovado.
O Secure MCP Tunnel serve para desenvolvimento privado; não o apresente como
endpoint público de produção.

Conduza as Ondas 1, 5, 6 e a parte open-source da Onda 7. Produza SDK/examples
Python e TypeScript mínimos, receitas de instalação limpa, conformance suite,
Playwright E2E, acessibilidade, visual QA, performance budget, link/claim checks
e handoff por wave em docs/handoffs/productization. Se um contrato estiver
ausente, registre o bloqueio e avance em mocks tipados sem inventar a API.

Só marque o goal concluído quando todos os deliverables sob sua responsabilidade
estiverem implementados, verificados e documentados. Não declare release GO:
integração final, holdout autorizado, CI remoto, publicação autorizada e S07-R2
independente são gates separados.
```

---

## 12. Backlog detalhado por domínio

### Segurança e privacidade

- [ ] revogar segredo exposto;
- [ ] secret scanning pre-commit/CI;
- [ ] data classification e data-flow diagram;
- [ ] hosted threat model;
- [ ] OAuth/OIDC conformance;
- [ ] scopes/consent/revocation;
- [ ] RLS adversarial suite;
- [ ] envelope encryption e key lifecycle;
- [ ] backup/restore/delete retention;
- [ ] privacy policy e subprocessors;
- [ ] DSAR/export/delete workflow;
- [ ] admin break-glass;
- [ ] prompt-injection/exfiltration defenses;
- [ ] private vulnerability reporting;
- [ ] external security review antes de GA.

### MCP e agentes

- [ ] Streamable HTTP;
- [ ] stdio parity;
- [ ] auth discovery;
- [ ] tool schemas/output schemas;
- [ ] annotations;
- [ ] idempotency e confirmations;
- [ ] resource/prompt support somente se houver caso real;
- [ ] protocol compatibility matrix;
- [ ] inspector/conformance automation;
- [ ] SDK Python/TS;
- [ ] client recipes e revocation tests.

### Dados e retrieval

- [ ] tenant-aware schema;
- [ ] migrations e rollback/forward-fix;
- [ ] E5 frozen profile;
- [ ] worker queue;
- [ ] stale vector protection;
- [ ] re-embedding resumível;
- [ ] language support matrix;
- [ ] eval governance;
- [ ] holdout sealed;
- [ ] quality/latency/cost reports por SHA;
- [ ] export/import versionado;
- [ ] consolidation com provenance.

### Web e marca

- [ ] naming ADR;
- [ ] design tokens;
- [ ] logo wordmark simples;
- [ ] landing responsiva;
- [ ] diagramas acessíveis;
- [ ] auth states;
- [ ] dashboard;
- [ ] compatibility page;
- [ ] docs;
- [ ] status/security/privacy pages;
- [ ] analytics consent;
- [ ] social preview após visual final;
- [ ] domínio e redirects.

### Operação e release

- [ ] dev/staging/prod separados;
- [ ] IaC;
- [ ] database pooling e migrations job;
- [ ] observability redaction;
- [ ] SLOs/alerts;
- [ ] incident/DR runbooks;
- [ ] load/chaos/restore tests;
- [ ] CI required checks;
- [ ] PVR/branch protection;
- [ ] SBOM/provenance/signing;
- [ ] clean installs;
- [ ] S07-R2 independente;
- [ ] autorização de publish.

---

## 13. Definition of Done do programa

O programa está concluído somente quando uma pessoa nova consegue:

1. abrir a landing e entender o produto, o controle e os limites de segurança;
2. criar conta por e-mail sem intervenção manual;
3. conectar ao menos cada superfície anunciada como Supported;
4. escrever uma memória, recuperá-la em outro cliente, corrigi-la e apagá-la;
5. inspecionar provenance e conexões no dashboard;
6. revogar um cliente e provar que seu token deixa de funcionar;
7. exportar seus dados e solicitar deleção;
8. observar que outro tenant não consegue acessar nada;
9. instalar a edição Community a partir de release versionada;
10. reproduzir testes e artifacts a partir do SHA publicado;
11. consultar documentação que não contradiz o comportamento;
12. verificar claims criptográficas apoiadas por testes e threat model;
13. encontrar canal de suporte e security reporting;
14. passar por backup/restore sem ressuscitar dados apagados;
15. ver CI remoto, supply-chain e auditoria S07-R2 em `GO`.

Se qualquer item falhar, o resultado pode ser um bom preview ou beta, mas ainda não é a produtização completa descrita aqui.

---

## 14. Referências técnicas oficiais para revalidação contínua

- OpenAI: MCP servers de produção devem usar endpoint HTTPS estável, Streamable HTTP e autorização quando acessam dados privados: <https://developers.openai.com/plugins/concepts/mcp-server>
- OpenAI: Secure MCP Tunnel é apropriado para servidor privado/testes, mas não substitui o endpoint público exigido para distribuição: <https://developers.openai.com/api/docs/guides/secure-mcp-tunnels>
- OpenAI: checklist de conexão e teste no ChatGPT: <https://developers.openai.com/plugins/deploy/connect-chatgpt>
- MCP specification/documentation: <https://modelcontextprotocol.io/docs/2026-07-28/getting-started/intro>
- Anthropic MCP connector: <https://platform.claude.com/docs/en/agents-and-tools/mcp-connector>
- Google Gemini CLI MCP configuration: <https://codelabs.developers.google.com/gemini-cli-deep-dive>

Essas integrações mudam. Luna deve revalidar as páginas oficiais no início de cada release e registrar a data, sem assumir que um fluxo antigo ainda existe.
