---
title: UMCP Roadmap Implementation Guide
status: active
confidence: repository-grounded
updated: 2026-08-29
baseline_roadmap: docs/CODEX_DELIVERY_ROADMAP.md
baseline_candidate: codex/m01-local-integrated@faeadaf
current_checkout_at_inventory: terra-alpha-recovery@2c94d55
---

# UMCP — guia de implementação do roadmap

## 1. Propósito e decisão executiva

Este documento é o guia operacional para concluir o roadmap definido em
`docs/CODEX_DELIVERY_ROADMAP.md`. Ele foi reconstruído a partir do estado real
do repositório entre 2026-08-21 e 2026-08-25: branches, commits, handoffs,
testes registrados, artefatos GCP presentes no worktree e uma verificação
somente leitura do endpoint de staging.

A leitura executiva é:

- **M0 está concluído apenas como readiness local em uma branch candidata.**
- **M1 está concluído apenas como readiness local em uma branch candidata.**
- **M2 está concluído em staging.** H07 demonstrou gateway, OAuth, tenancy/RLS,
  KMS, restore e operação na revisão `umcp-cloud-staging-00018-f78`. Isso não
  significa production-ready.
- **M3 está em execução.** C01/C02 possuem implementação e uma rodada hosted
  verde, mas permanecem abertos até a auditoria ser repetida por uma imagem
  construída de um SHA limpo e reproduzível. C03–C05 continuam pendentes.
- **M4–M8 permanecem majoritariamente por implementar.**
- **Nenhuma entrega posterior ao Alpha está integrada em `main`.**
- **O primeiro uso externo será private managed beta; M7 open source vem
  depois de M6, não antes.**
- **A primeira tarefa não é abrir uma feature nova; é criar uma linha
  canônica, limpa e auditável que reúna as entregas válidas já existentes.**

Este guia não transforma presença de código em `GO`. Para este documento,
“entregue” significa: integrado no candidato canônico, demonstrado no mesmo
SHA, gates atuais executados, handoff reconciliado e worktree limpa.

## 2. Fontes obrigatórias

Toda sessão deve ler, no mínimo:

1. `docs/PRODUCT_VISION_PORTABLE_MEMORY.md`;
2. `docs/CODEX_DELIVERY_ROADMAP.md`;
3. este `docs/roadmap_implementation.md`;
4. `docs/GAMEPLAN_PRODUCTIZATION_TERRA_LUNA.md`;
5. `docs/EXECUTION_RELIABILITY_PLAYBOOK.md`;
6. ADRs e contratos citados no pacote;
7. o handoff do pacote imediatamente anterior;
8. os handoffs específicos listados neste guia, inclusive quando existirem
   somente em outra branch/commit.

Fontes complementares já produzidas e que devem ser incorporadas à linha
canônica no primeiro bloco de integração:

- `docs/handoffs/roadmap/M03-M08-PRODUCT-EXECUTION-PLAN.md` no commit
  `4639f7f`;
- `docs/execution/mcp-readiness/01-BASELINE-LOCAL-MCP.md` até
  `08-BETA-RELEASE-READINESS.md` no commit `de9ba6d`;
- `docs/handoffs/roadmap/M02-GCP-ADOPTION-GAP-REPORT.md` no commit `106ec89`;
- `docs/handoffs/roadmap/M02-HOSTED-CONTRACT.md` no commit `ef949f3`.

### Navegação do candidato R01

Os artefatos documentais integrados por R01 estão disponíveis em:

- [plano de execução M03–M08](handoffs/roadmap/M03-M08-PRODUCT-EXECUTION-PLAN.md);
- [índice de readiness MCP local](execution/mcp-readiness/01-BASELINE-LOCAL-MCP.md);
- [transporte MCP remoto](execution/mcp-readiness/02-REMOTE-MCP-TRANSPORT.md);
- [auth, consentimento e revogação](execution/mcp-readiness/03-AUTH-CONSENT-REVOCATION.md);
- [multitenancy e segurança](execution/mcp-readiness/04-MULTITENANCY-SECURITY.md);
- [conectores de clientes reais](execution/mcp-readiness/05-REAL-CLIENT-CONNECTORS.md);
- [UX e landing](execution/mcp-readiness/06-PRODUCT-UX-AND-LANDING.md);
- [trusted recall](execution/mcp-readiness/07-TRUSTED-RECALL.md);
- [beta e release readiness](execution/mcp-readiness/08-BETA-RELEASE-READINESS.md);
- [gap report da adoção GCP](handoffs/roadmap/M02-GCP-ADOPTION-GAP-REPORT.md).

R01 integra somente documentação e links. Os playbooks e o plano são
`integrated-current` como artefatos documentais no SHA final; seus gates de
produto permanecem `not-run` até os pacotes que os implementarem. O gap report
é a classificação vigente dos artefatos GCP: proposta local, `PARTIAL /
NOT-READY`, sem evidência de deploy, billing, URL, OAuth, RLS, KMS, restore ou
produção. Nenhum claim `DONE`, `VERIFIED` ou `PRODUCTION-READY` de GCP é
promovido por R01.

## 3. Regra de evidência

### 3.1 Rótulos obrigatórios

| Rótulo | Significado |
| --- | --- |
| `integrated-current` | presente no candidato canônico e testado no mesmo SHA |
| `branch-only` | commit existente, mas ainda fora do candidato canônico |
| `worktree-only` | arquivo presente sem commit na inspeção de 2026-08-25 |
| `remote-observed` | comportamento remoto observado, sem inferir controles internos |
| `historical` | teste ou claim registrado em SHA anterior e ainda não repetido |
| `environment-blocked` | comando realmente tentado e bloqueado pelo ambiente |
| `not-run` | não executado; nunca equivale a pass |
| `claim-only` | documento afirma algo que a evidência disponível não sustenta |

### 3.2 Hierarquia de confiança

Da maior para a menor força:

1. acceptance test e demo executados no SHA canônico limpo;
2. teste atual no commit da lane, ainda não integrado;
3. teste histórico documentado;
4. código/configuração inspecionados;
5. handoff declaratório;
6. nome de arquivo, status textual, healthcheck ou UI isolada.

Um `/health`, `/healthz` ou `/readyz` verde prova somente a rota que respondeu.
Não prova MCP, auth, banco, RLS, KMS, backup, restore ou segurança.

## 4. Inventário do que foi entregue desde 21/08

### 4.1 Topologia Git observada em 25/08

| Linha | HEAD/estado | Leitura correta |
| --- | --- | --- |
| `main` | `4947ebf` | Alpha baseline; não contém o programa de productization |
| `terra-alpha-recovery` | `2c94d55` + alterações locais | checkout atual na inspeção; não contém M0/M1 integrados |
| `roadmap/integration` | `8bcd044` | integração/evidência M0, anterior ao M1 final |
| `codex/m01-local-integrated` | `faeadaf` | melhor candidato integrado local para M0+M1 |
| `codex/m02-hosted-contract` | `ef949f3` | contrato M2, baseado em M1 |
| `codex/m02-provider-decision` | `cfbbd24` | recomendação AWS histórica; GCP foi adotado depois sem ADR reconciliada |
| `codex/m02-gcp-state` | `275fa1a` | registrou bloqueio de billing posteriormente resolvido fora da branch |
| `codex/m02-hosted-trust-boundary` | `81e6a33` | seam local fail-closed, sem IdP real e sem `/mcp` público |
| detached hosted gateway | `39c01a1` | composição local do seam; sem deploy e sem OAuth real |
| `codex/m03-connector-contract` | `e6071eb` | contrato v1 e conformance sintética |
| detached connector recipe | `37b2fb3` | receita sintética reprodutível, sem cliente real |
| `codex/m03-m08-product-plan` | `4639f7f` | plano detalhado, baseado na branch antiga e não integrado |
| detached readiness playbooks | `de9ba6d` | oito playbooks de execução, não integrados |
| GCP atual | `worktree-only` | Docker/IaC/workflow/runtime/handoff sem commit na inspeção |

Consequência: nenhuma nova sessão deve assumir que o checkout atual é o
baseline correto. A linha de implementação deve nascer de
`codex/m01-local-integrated@faeadaf` e incorporar seletivamente os artefatos
posteriores, com conflitos e gates resolvidos no mesmo candidato.

### 4.2 Linha do tempo material

#### 21/08 — M0 e governança de execução

Foram produzidos:

- integração local das fundações Terra e Luna;
- gateway MCP HTTP, Admin API e web shell locais no trabalho de
  productization;
- RLS/multitenancy, encryption envelope, workers, tombstones e controles
  locais com cobertura registrada;
- scripts de demo, gate freshness, preflight de worktree e coordenação;
- evidência de evals development em português e inglês;
- auditorias e handoffs M0, incluindo limitações de browser E2E e dependency
  audit;
- `CODEX_DELIVERY_ROADMAP.md`, visão de produto e playbook de confiabilidade.

Classificação: `branch-only`, com decisão local `READY`, sem release e sem
produção.

#### 22/08 — M1 Portable Memory Local

Foram produzidos:

- estados `candidate`, `confirmed`, `pinned` e `stale`;
- `mental_note`, spaces, provenance e capture consent;
- lifecycle, idempotência, version conflict e tombstone blocking;
- migration `0008_m1_local_memory_contract`;
- oito tools M1 estritas no adapter MCP HTTP local;
- principal local derivado de token, scopes e revogação por conexão;
- Memory Inbox web com confirmação, edição, descarte, provenance, consent e
  estados de lifecycle;
- harness ASGI e cenário cross-client completo;
- decisão `M01-READY` em `faeadaf`.

Limitações preservadas:

- socket HTTP black-box ficou `environment-blocked` no ambiente da sessão;
- browser E2E conectado não foi executado;
- PostgreSQL descartável não foi exigido no fechamento sintético M1;
- o resultado não é hosted, release ou produção.

Classificação: `branch-only`, melhor baseline funcional atual.

#### 24/08 — preparação M2/M3 e plano M3–M8

Foram produzidos:

- contrato hosted M2 e capacidade mínima M02-C1;
- comparação de providers e recomendação AWS, depois superada de fato pela
  adoção GCP, ainda sem ADR formal de substituição;
- seam local de autenticação hosted com `CredentialVerifier`, `Principal`
  imutável e rejeição de `owner_id`/`tenant_id` do request;
- composição local do hosted gateway, deliberadamente sem `/mcp` público;
- contrato MCP connector v1, fixtures e conformance sintética;
- receita sintética capture/recall/update/forget/revoke;
- plano de produto M03–M08 e oito playbooks de readiness;
- relatório de gaps GCP com blockers P0/P1.

Classificação: `branch-only`; nenhuma dessas lanes fecha M2 ou M3.

#### 25/08 — GCP staging

Foram encontrados no worktree:

- `Dockerfile`;
- `.github/workflows/gcp-deploy.yml`;
- `ops/terraform/gcp/`;
- `scripts/deploy-gcp.sh`;
- `src/omp/server/http.py`;
- `docs/runbooks/gcp-deployment.md`;
- `docs/handoffs/roadmap/M02-GCP-DEPLOYMENT-DONE.md`.

O endpoint informado respondeu, na inspeção de 25/08:

- `/health` com HTTP 200;
- `/readyz` com HTTP 200;
- `/openapi.json` com HTTP 200 e apenas health/readiness visíveis;
- `/mcp` com redirect 307 para uma URL `http://`;
- `/mcp/` com HTTP 404;
- `/healthz` apresentou resposta inconsistente em uma das verificações.

Portanto, existe um serviço Cloud Run observável, mas o MCP remoto exigido não
está funcional em `/mcp` e o redirect viola o requisito de não fazer downgrade
de HTTPS. O handoff `M02-GCP-DEPLOYMENT-DONE.md` deve ser reclassificado de
`DONE / VERIFIED` para `PARTIAL / NOT-READY` até auditoria posterior.

## 5. Dashboard real do roadmap

| Marco | Estado em 25/08 | Entregue | Falta para o gate |
| --- | --- | --- | --- |
| M0 | `READY local / branch-only` | integração, gates locais, demos, evidência e auditoria | integrar na linha canônica, repetir freshness e resolver bloqueios relevantes |
| M1 | `READY local / branch-only` | core capture, tools, Inbox e ASGI cross-client | repetir PostgreSQL, HTTP black-box e browser E2E no candidato canônico |
| M2 | `PARTIAL / NOT-READY` | contrato, seams hosted locais, IaC inicial e Cloud Run observável | MCP remoto válido, OAuth/OIDC, consent, private SQL, FORCE RLS, KMS real, restore, observability e auditoria |
| M3 | `PREFLIGHT only` | contrato v1, fixtures e recipe sintética | controlled Python agent e duas superfícies reais com auth/revoke/report |
| M4 | `NOT-STARTED`, exceto Inbox M1 | Inbox local e primitives de mental note | concepts domain/jobs/API, Concepts UI, Notes completas, Activity e invalidação |
| M5 | `BASELINE only` | E5 development evidence e harnesses iniciais | capture/recall/security evals, policy engine, workers, budgets e thresholds |
| M6 | `NOT-STARTED` private managed beta | alguns controles locais reutilizáveis | onboarding real, quotas, telemetry opt-in, drills, SLO, suporte e beta aprovado; sem distribuição pública |
| M7 | `DEFERRED until M6 evidence` | Alpha possui packaging/docs parciais | clean install, multi-arch, CI remoto, scans, SBOM/provenance/signing e auditoria após B04T |
| M8 | `NOT-STARTED` | nenhum gate de beta público/GA | operação sustentada, claims e auditorias, holdout autorizado e decisão humana |

## 6. Findings que bloqueiam avanço

### P0 — baseline fragmentado

O checkout atual não contém M0/M1 integrados, enquanto as implementações M2 e
M3 estão em forks diferentes ou commits destacados. Construir a partir da
branch errada pode apagar capacidades ou criar falsos merges.

Fechamento: candidato canônico limpo, baseado em `faeadaf`, com todos os
artefatos válidos integrados seletivamente e gates repetidos.

### P0 — endpoint hosted não é MCP utilizável

`/mcp` redireciona de HTTPS para HTTP e `/mcp/` responde 404. Health/readiness
não substituem initialize, tools/list e tools/call.

Fechamento: conformance MCP black-box por HTTPS, sem downgrade, com sessão,
reconnect, timeout e erro seguro.

### P0 — runtime público sem trust boundary real

O Terraform e o deploy imperativo usam acesso não autenticado. O runtime GCP
monta o adapter local e não integra os seams hosted de `81e6a33`/`39c01a1`.
Não há IdP real, JWKS, issuer/audience, PKCE, consent ou revogação comprovados.

Fechamento: borda fail-closed integrada ao `/mcp`, OAuth/OIDC real em staging e
suite adversarial atual.

### P0 — plano de dados GCP inseguro/incompleto

O IaC atual usa IPv4 público no Cloud SQL, conexão `localhost` sem connector,
senha interpolada, ausência de service accounts explícitas e Secret Manager
não consumido pelo runtime. KMS existe apenas como primitive de IaC.

Fechamento: SAs mínimas, WIF, rede privada, conexão Cloud SQL suportada,
segredos referenciados, KMS adapter fail-closed e Terraform state protegido.

### P0 — Gate M2 de dados e recuperação ausente

Não há prova hosted atual de FORCE RLS, tenant context, backup→restore,
tombstones, rotação/rewrap, ciphertext swap ou cross-tenant adversarial.

Fechamento: migrations e testes reais no staging isolado, com evidência
redigida no mesmo revision/digest.

### P1 — claims e automação superestimam readiness

O runbook diz `PRODUCTION-READY` e o handoff diz `DONE / VERIFIED`, embora o
gate esteja aberto. O workflow usa chave JSON estática e possui divergência de
porta; o script mistura enable APIs, build, apply automático, fallback e
deploy público.

Fechamento: corrigir claims, separar plan/apply/migrate/deploy/verify, usar WIF
e promover somente imagem por digest após aprovação.

## 7. Modelo para sessões pequenas

### 7.1 Escolha do modelo

Use **GPT Terra** para:

- arquitetura, integração e migrations;
- domínio/application services;
- auth, tenancy, RLS, crypto, workers e operações;
- IaC, CI/CD e gates de segurança;
- evals, desempenho e release engineering.

Use **GPT Luna** para:

- produto web, UX, acessibilidade e visual QA;
- SDKs, recipes e conectores;
- compatibility matrix, docs e claim matrix;
- conformance orientada à experiência;
- onboarding, feedback e materiais de release.

Use uma sessão Terra limpa, que não tenha escrito o pacote, para auditorias em
que Sol não esteja disponível. Auditoria nunca deve ocorrer na mesma sessão
autora.

### 7.2 Contrato de cada sessão

Cada sessão recebe apenas um ID deste guia e deve:

1. confirmar worktree, branch, base SHA e status;
2. ler o contrato e handoff anterior completos;
3. congelar acceptance test antes da implementação principal;
4. alterar somente os paths reservados;
5. produzir uma demo ou comando de aceitação único;
6. executar testes focados e regressão proporcional;
7. registrar `current`, `historical`, `not-run` e `environment-blocked`;
8. criar commits locais pequenos;
9. produzir `docs/handoffs/roadmap/<ID>-DONE.md`;
10. terminar com worktree sem resíduo da própria lane.

Não autorizado por este guia: dados reais, holdout, convite a usuários, push,
PR, tag, release, produção, DNS, e-mail real, compra ou aumento de custo. Uma
sessão que dependa disso conclui todo trabalho local e registra o checkpoint de
autorização sem simular o resultado externo.

## 8. Sequência de implementação

O caminho crítico é:

```text
R00–R02 consolidar baseline
  → H01–H07 fechar M2 hosted
  → C01–C05 provar M3 real
  → A01–A05 entregar M4 Atlas
  → T01–T05 fechar M5 Trusted Recall
  → B01–B04 preparar/operar private managed beta M6
  → O01–O04 fechar M7 open source após evidência M6
  → G01–G03 decidir M8
```

Somente sessões explicitamente marcadas como paralelas podem coexistir, e
apenas após o contrato compartilhado estar congelado.

## 9. Bloco R — consolidação do baseline

### R00 — criar candidato canônico

**Modelo:** Terra.  
**Base:** `codex/m01-local-integrated@faeadaf`.  
**Objetivo:** criar uma branch `codex/roadmap-implementation` ou equivalente,
sem alterar `main`, e provar que M0+M1 estão preservados.

Entregar:

- branch/worktree exclusiva baseada exatamente em `faeadaf`;
- inventário de commits e branches posteriores;
- repetição de unit, contract, conformance, web build/test/check e migrations
  disponíveis;
- classificação atual dos bloqueios de PostgreSQL, socket e browser;
- `R00-CANONICAL-BASELINE-DONE.md` com SHA e outputs.

Gate:

- árvore limpa;
- cenário M1 ASGI verde;
- web build/test/check verdes;
- nenhum arquivo GCP ou M2 incorporado ainda;
- divergência contra `main` e `terra-alpha-recovery` documentada.

### R01 — integrar documentação e playbooks pós-M1

**Modelo:** Luna.  
**Depende de:** R00.  
**Pode rodar em paralelo com:** R02 somente com paths exclusivos.

Incorporar seletivamente:

- plano M03–M08 de `4639f7f`;
- playbooks de `de9ba6d`;
- gap report GCP de `106ec89`;
- este guia e links de navegação;
- correção dos claims `DONE`, `VERIFIED` e `PRODUCTION-READY` dos artefatos
  GCP para `PARTIAL / NOT-READY`.

Gate:

- nenhum código antigo é revertido pelo fato de os commits-fonte nascerem de
  `2c94d55`;
- links locais válidos;
- nenhum claim de provider/produção sem evidência;
- docs distinguem candidato local, staging e release.

### R02 — integrar lanes M2/M3 locais válidas

**Modelo:** Terra.  
**Depende de:** R00.  
**Paths:** `src/omp/server/`, `src/omp/adapters/mcp/`, `docs/contracts/mcp/v1/`,
`examples/connectors/`, testes associados e handoffs.

Incorporar seletivamente:

- hosted trust boundary `81e6a33`;
- hosted gateway local `5d48fd3` + correção `39c01a1`;
- connector contract `7f77314` + correção `e6071eb`;
- connector recipe `79c559d` + correção `37b2fb3`.

Não incorporar ainda o runtime GCP público como se fosse solução final.

Gate:

- testes hosted fail-closed verdes;
- M1 continua verde;
- conformance v1 e recipe sintética verdes;
- seams locais continuam explicitamente não publicáveis;
- todos os commits integrados no mesmo candidato limpo.

## 10. Bloco H — M2 Identity & Hosted Alpha

### H01 — reconciliar a decisão GCP e congelar arquitetura

**Modelo:** Terra.  
**Depende de:** R01 e R02.

Entregar:

- ADR formal substituindo a recomendação AWS por GCP, com região
  `southamerica-east1`, budget, data-residency limitada e exit path;
- desenho de projetos/ambientes, runtime/migration/deploy SAs, IAM mínimo e
  GitHub WIF;
- desenho de VPC, Private Service Access, Cloud SQL privado e connector;
- decisão de IdP/e-mail, após spike de no máximo dois candidatos;
- matriz Secret Manager/KMS e ownership de chaves;
- threat-model delta e rollback.

Gate: decisões explícitas, nenhuma credencial no Git, nenhuma ação externa
adicional inferida e interfaces aceitas para H02–H05.

### H02 — endurecer IaC e pipeline GCP

**Modelo:** Terra.  
**Depende de:** H01.  
**Paths:** `ops/terraform/gcp/`, `.github/workflows/`, `scripts/`, Dockerfile e
runbook de infraestrutura.

Entregar:

- remover `allUsers` e `--allow-unauthenticated` do desenho de runtime;
- SAs explícitas e IAM mínimo;
- WIF no lugar de `GCP_SA_KEY`;
- Cloud SQL sem IPv4 público, conexão privada e role separada de migration;
- Secret Manager referenciado sem valor secreto no env/plan;
- state remoto protegido, locking e política de acesso;
- budget/alerts, Logging/Monitoring básicos e retenção;
- imagem por digest, portas consistentes e sem fallback imperativo;
- `terraform fmt`, `validate`, lint de workflow e plan redigido.

Gate: plan revisado sem criação destrutiva inesperada; apply externo continua
checkpoint separado.

### H03 — compor MCP Streamable HTTP hosted corretamente

**Modelo:** Terra.  
**Depende de:** R02 e H01.  
**Paths:** `src/omp/server/`, `src/omp/adapters/mcp/`, tests contract/E2E.

Entregar:

- `/mcp` oficial sem redirect para HTTP e sem rota duplicada;
- mesma application façade para stdio, M1 local HTTP e hosted HTTP;
- lifecycle, session, reconnect, cancellation, timeout e request ID;
- health/readiness separados e truthful: readiness falha se DB/KMS/IdP
  obrigatório estiver indisponível;
- host allowlist, proxy headers confiáveis e rate-limit seam;
- conformance black-box local por HTTP.

Gate: initialize, tools/list e tools/call verdes no endpoint exato `/mcp`;
nenhum healthcheck usado como substituto.

### H04 — implementar OAuth/OIDC, consentimento e revogação

**Modelo:** Terra para backend.  
**Depende de:** H01 e H03.

Entregar:

- authorization code + PKCE;
- protected-resource e authorization-server metadata;
- JWKS/signature, issuer, audience/resource, `exp`, `nbf` e client binding;
- `Principal` imutável derivado apenas do token/registro server-side;
- scopes mínimos, consent record versionado, connection binding;
- access/refresh/PAT revocation e rotação;
- callback allowlist, anti-enumeration e abuse controls;
- testes para token ausente, expirado, revogado, issuer/audience errados,
  scope insuficiente e `owner_id`/`tenant_id` forjados.

Gate: nenhum request inválido invoca application service ou banco; logs não
contêm token, cookie, e-mail, query ou memória.

### H05 — login e consent UX

**Modelo:** Luna.  
**Depende de:** contrato H04 congelado.  
**Pode rodar em paralelo com:** H06.

Entregar:

- `/login`, callback e sessão server-side;
- Continue with Google e magic-link somente para o IdP escolhido;
- consent screen com cliente, scopes, finalidade e revogação;
- `/connections` com estado, scopes, last-used audit-safe e revoke;
- loading, retry, expired, denied e revoked states;
- teclado, mobile, reduced motion e WCAG AA;
- browser E2E contra provider sandbox autorizado ou fixture contratual sem
  chamar fixture de hosted pass.

Gate: browser nunca decide tenant/scope e nunca guarda credencial durável;
revoke real bloqueia a sessão correspondente quando integrado.

### H06 — tenancy, RLS, KMS e recuperação hosted

**Modelo:** Terra.  
**Depende de:** H01 e H04.  
**Paths:** migrations, PostgreSQL adapters, cloud encryption/worker e testes.

Entregar:

- `tenant_id` em todos os aggregates hosted e FKs/índices compostos;
- FORCE RLS default-deny em todas as tabelas tenant-owned;
- roles runtime, migration e break-glass separadas;
- tenant context transaction-local somente após principal verificado;
- envelope encryption server-decryptable com DEK por tenant, KEK no GCP KMS,
  AAD e key versions;
- fail-closed em KMS failure, ciphertext swap e key mismatch;
- backups/PITR inventariados, restore em alvo isolado, tombstone replay e
  RPO/RTO observados;
- jobs tenant-bound, expiry/nonce/dedupe, retry e DLQ;
- suite cross-tenant para query, mutate, export, worker, restore e delete.

Gate: leakage zero, sem fallback plaintext, restore não ressuscita forget e
observability redigida.

### H07 — integração e auditoria M2 em staging

**Modelo:** Terra em sessão limpa de auditoria.  
**Depende de:** H02–H06.

Executar no mesmo revision/digest:

1. TLS e MCP `/mcp` black-box;
2. login Google/e-mail autorizado;
3. duas conexões para a mesma identidade;
4. token/scope/revoke adversarial;
5. owner/tenant forjado;
6. cross-tenant RLS;
7. KMS failure/swap/rotation;
8. backup→restore→tombstones;
9. secret/log scan;
10. load baseline e alertas.

Gate M2: CONCLUÍDO (2026-08-28). Todos os 23 gates da matriz H07 aprovados em staging (SHA `367cd365df43f9282f5155394cd39275169bf8f2`, digest `sha256:764263db4907ffbbbd50e77ab7d12e8d88cde2b5990a9879a40ddbd0976e4f1d`, revisão `umcp-cloud-staging-00018-f78`, migration `umcp-migrate-staging-w9ld8`, drill KMS hosted e drill de restore hosted real com Backup ID `1787875200000` / Restore Op ID `20230b7b-50c0-461e-84ec-cfc900000032`). Handoff formalizado em `docs/handoffs/roadmap/H07-AUDIT-20260828.md`: **`M02 STAGING READY`** (não é production-ready).

## 11. Bloco C — M3 Cross-client Connectors

### C01 — runner comum e SDK Python

**Modelo:** Luna.  
**Depende de:** H07.

Entregar:

- runner real sobre o contrato v1 já existente;
- SDK Python fino sem regra de negócio duplicada;
- discovery, OAuth, token refresh, scopes, retries seguros e redaction;
- reports datados/checksummed;
- prompts positivos, indiretos, negativos e destrutivos;
- matriz `Supported / Experimental / Unverified`.

Estado C01 (2026-08-29): implementação pronta e rodada hosted 14/14 PASS, com
artefatos datados/checksummed. Gate reaberto até repetir a auditoria usando uma
imagem construída de um commit limpo cujo SHA seja exatamente o
`audit_source_sha`. A rodada atual usa o digest imutável
`sha256:c39b3d02785b0a4f817da4074136b4d662c49085499e6cebbf8a69b96ccbedea`,
mas registra `72b9fad4...` enquanto o código executado foi commitado somente em
`b462bcce...`. Ver `docs/handoffs/roadmap/MVP-RESUMPTION-20260829.md`.

### C02 — primeiro conector real controlado

**Modelo:** Luna; Terra apenas para findings do gateway.  
**Depende de:** C01.

Executar write/capture, recall, update, forget, revoke, unauthorized e
provenance em um agente Python controlado pelo projeto. Registrar versão,
data, scopes, report ID e limitações.

Estado C02 (2026-08-29): implementação pronta e rodada hosted 15/15 PASS, com
contenção final `active_tokens=0`, `active_codes=0` e
`active_test_tenants=0`. Gate reaberto pelo mesmo desvio de proveniência da
imagem de auditoria de C01; fechar somente após reexecução limpa vinculada ao
SHA exato. Ver `docs/handoffs/roadmap/MVP-RESUMPTION-20260829.md`.

### C03 — primeira superfície externa real

**Modelo:** Luna.  
**Depende de:** C02 e autorização para credencial/cliente externo.

Prioridade: ChatGPT developer mode. Se capability preflight atual impedir o
fluxo completo, classificar honestamente e usar Claude API/cliente documentado
como alternativa, sem chamar a tentativa falha de suporte.

Gate: cenário real, recipe limpa, report checksummed e compatibility matrix.

### C04 — segunda superfície externa real

**Modelo:** Luna.  
**Depende de:** C03.

Executar em uma superfície diferente da primeira. Provar A registra → B
recupera e, quando suportado, B registra → A recupera. Incluir update, forget,
revoke e erro seguro.

Gate: duas superfícies reais diferentes, além do agente controlado, ou decisão
explícita do roadmap revisando o requisito.

### C05 — auditoria M3 e SDK TypeScript

**Modelo:** Luna para SDK; Terra limpa para auditoria.  
**Depende de:** C03 e C04.

Entregar SDK TypeScript mínimo, recipes finais, reports verificáveis, matriz
datada e auditoria de claims. Gemini CLI e superfícies adicionais permanecem
`Experimental`/`Unverified` até execução real.

Gate M3: pelo menos dois clientes reais completam a jornada e nenhum claim
universal é publicado.

## 12. Bloco A — M4 Memory Atlas

### A01 — concepts domain e migrations

**Modelo:** Terra.  
**Depende de:** C05.

Entregar `concepts`, `memory_concepts`, relações, salience, summaries
versionados, provenance, APIs paginadas e migrations aditivas. Toda relação
deve apontar para memórias de suporte e para a versão-fonte.

Gate: update/forget/stale invalidam derivados; retry não duplica conceitos.

### A02 — jobs de consolidação

**Modelo:** Terra.  
**Depende de:** A01.

Entregar jobs idempotentes, tenant-bound, retry/DLQ/backpressure, source
version e recalculation. Tratar memória como dado não confiável, nunca como
instrução do sistema.

Gate: restart/retry, cross-tenant, stale vector e delete-during-job verdes.

### A03 — Inbox e Connections reais

**Modelo:** Luna.  
**Depende de:** H05, C05 e APIs A01 congeladas.  
**Pode rodar em paralelo com:** A02 e A04.

Substituir fixtures por adapters reais para candidate origin/reason,
confirm/edit/discard, never-category, policy por conexão, revoke e recall no
segundo cliente.

Gate: ação na UI altera o recall hosted real; backend failure mostra erro, não
dado inventado.

### A04 — Concepts UI

**Modelo:** Luna.  
**Depende de:** contrato A01.

Entregar lista/detalhe/busca/filtros, resumo, support memories, relações em
lista acessível, evolução, perguntas abertas e why/provenance. Grafo é
opcional e sempre tem alternativa textual.

Gate: teclado/mobile/WCAG AA e nenhum conceito sem suporte rastreável.

### A05 — Mental Notes, Activity e auditoria M4

**Modelo:** Terra para domínio/API; Luna para UI; auditor em sessão limpa.  
**Depende de:** A01–A04.

Entregar notes/goals/decisions/open questions, pin/unpin, mover de espaço,
relacionar conceito, resolver/arquivar/forget, Activity audit-safe e “why
recalled?”.

Gate M4: forget invalida derivados; inferência pode ser corrigida; UI completa
por teclado/mobile; telemetry sem payload ou chain-of-thought.

## 13. Bloco T — M5 Trusted Recall

### T01 — governança e corpus development

**Modelo:** Terra.  
**Depende de:** A05.

Congelar schemas, manifests, checksums, slices e thresholds antes das medições.
Separar português/inglês, development/holdout e capture/retrieval/security.

Gate: holdout permanece inacessível e `not-run` sem autorização específica.

### T02 — capture, policy, dedupe e conflito

**Modelo:** Terra.  
**Depende de:** T01.

Medir capture precision, candidate accept/edit/reject, never-store violation,
dedupe, contradictions, stale/outdated e cross-space policy. Entregar policy
engine manual/assisted/automatic com rollback para modo conservador.

Gate: category-policy violation zero e metas não alteradas após o resultado.

### T03 — recall, abstention e segurança

**Modelo:** Terra.  
**Depende de:** T01 e T02.

Medir precision@k, intrusion, abstention, useful recall, provenance e
wrong-memory confirmation por slice. Testar prompt injection, memory poisoning,
instruction/data separation, revoke e cross-tenant.

Gate: leakage zero, poisoning controlado e claims limitadas aos corpora.

### T04 — workers, desempenho e custo

**Modelo:** Terra.  
**Depende de:** T02 e T03.

Fechar queues, idempotência, retry/DLQ, backpressure, source versions, p50/p95/
p99 e budgets de custo. Produzir load report sintético por SHA/config/profile.

Gate: nenhum worker executa sem tenant/envelope válido; budgets pré-definidos.

### T05 — feedback UX e decisão M5

**Modelo:** Luna para UX; Terra limpa para auditoria.  
**Depende de:** T02–T04.

Entregar feedback opt-in agregado, estados de confidence/abstention/conflict e
relatórios redigidos. Solicitar holdout somente com candidate SHA congelado.

Gate M5: development atende guardrails; holdout continua `not-run` ou tem uma
única execução autorizada; falha produz `NO-GO`.

## 14. Bloco B — M6 Private Managed Beta

### B01 — onboarding e controles de usuário

**Modelo:** Luna.  
**Depende de:** T05.

Entregar onboarding, explicação de captura, setup de conexões, scopes, revoke,
export/delete, privacy/support/security e feedback taxonomy.

Gate: pessoa nova entende o que é capturado e controla lifecycle completo.

### B02 — operação, quotas e console

**Modelo:** Terra.  
**Depende de:** T05.

Entregar feature flags, quotas, kill switches, admin console audit-safe,
analytics opt-in agregada, cost/capacity dashboards, abuse e security intake.

Gate: operador observa serviço sem leitura casual de conteúdo.

### B03 — drills e beta readiness

**Modelo:** Terra.  
**Depende de:** B01 e B02.

Executar incident, credential compromise, restore/delete/tombstone, rollback e
capacity drills. Observar SLO e RPO/RTO, sem prometer metas ainda não medidas.

Gate: nenhum P0/P1 aberto, rollback ensaiado, canais e owners ativos.

### B04 — abertura controlada do beta

**Modelo:** Luna para onboarding/suporte; Terra para operação.  
**Depende de:** B03 e autorização humana explícita.

Abrir somente 5–20 usuários consentidos, com quotas e kill switch. Código,
SDKs, artefatos e documentação operacional permanecem privados. Registrar
coorte, consentimento, incidentes, custo e critérios de pausa sem conteúdo em
analytics.

Gate M6: SLO observado, restore/delete comprovados e usuários compreendem
captura/controle. Sem autorização, concluir como `BETA-READY / NOT-OPENED`.

## 15. Bloco O — M7 Open-source Release após beta privado

### O01 — clean install e artefatos

**Modelo:** Terra.  
**Depende de:** B04T. O beta privado precisa ter sido operado e auditado antes
de expor uma superfície Community suportada.

Entregar quickstart limpo, wheel/sdist, migrations empacotadas, Docker
multi-arch, constraints, upgrade/forward-fix/restore e sample runtime.

Gate: instalação limpa nas plataformas declaradas e journey local completa.

### O02 — SDKs, examples e documentação Community

**Modelo:** Luna.  
**Depende de:** O01.

Entregar agents Python/TypeScript, recipes, support matrix, compatibility,
privacy, security, governance, contributing, DCO, CODEOWNERS e templates.

Gate: links/claims verdes e nenhuma dependência hosted apresentada como
Community.

### O03 — supply chain e CI

**Modelo:** Terra.  
**Depende de:** O01.

Entregar required CI, secret/dependency/license scans, SBOM, checksums,
provenance/signing, changelog, semantic versioning e vulnerability reporting.

Gate: build reproduzível a partir de SHA limpo e artefatos vinculados ao SHA.

### O04 — auditoria independente M7

**Modelo:** Terra em sessão limpa ou Sol.  
**Depende de:** O01–O03.

Executar suite, clean install, package audit, scans, docs/links, migrations,
backup/restore/delete e auditoria equivalente a S07-R2.

Gate M7: `GO` independente. Publicação, push, tag e release continuam ações
separadas e exigem autorização humana; M7 não reclassifica o beta privado como
public beta ou GA.

## 16. Bloco G — M8 Public Beta e GA

### G01 — public beta readiness

**Modelo:** Terra + Luna em lanes separadas.  
**Depende de:** B04, O04 e autorização humana.

Entregar onboarding self-service, quotas/custos/suporte, status page, privacy e
subprocessors, monitoring/alerts, abuse testing e feedback loops.

Gate: capacidade e operação comprovadas; conectores anunciados possuem reports
atuais.

### G02 — candidato GA

**Modelo:** Terra.  
**Depende de:** G01 e período de SLO sustentado.

Congelar candidate SHA/digest; auditar auth/RLS/crypto, threat model,
backup/restore/delete em produção, incident drills, compatibility e claims.
Executar holdout apenas se autorizado e uma única vez no SHA congelado.

Gate: nenhuma inferência de GA a partir de deploy, uptime curto ou demo.

### G03 — decisão humana de lançamento

**Modelo:** Luna prepara claims/release notes; auditor produz recomendação.  
**Depende de:** G02.

Entregar pacote de decisão com GO/NO-GO, findings, SLO observado, custos,
compatibilidade, riscos residuais, rollback e ações externas exatas.

Gate M8: autorização humana explícita para Public Beta ou GA. Sem autorização,
estado final é `RELEASE-READY / NOT-PUBLISHED`.

## 17. Checkpoints humanos obrigatórios

| Checkpoint | Antes de quê | Decisão necessária |
| --- | --- | --- |
| CP-1 | apply GCP adicional | projeto, região, budget, owner e blast radius |
| CP-2 | IdP/client registration | provider, redirect URIs, scopes, e-mail e custos |
| CP-3 | secrets/KMS/IAM externos | owners, rotação, break-glass e revogação |
| CP-4 | clientes ChatGPT/Claude/Gemini | credenciais, endpoint e uso de serviço |
| CP-5 | holdout | SHA, thresholds, dataset e execução única |
| CP-6 | beta fechado | usuários, consentimento, suporte, quotas e incident channel |
| CP-7 | push/PR/tag/release | alvo remoto e artefatos exatos |
| CP-8 | public beta/GA | claims, SLO, custos, riscos e rollback |

## 18. Prompt-base para cada sessão

```text
Execute somente o pacote <ID> de docs/roadmap_implementation.md.

Leia integralmente os documentos obrigatórios, o contrato do pacote e o
handoff anterior. Confirme worktree, branch, base SHA e árvore limpa. Congele o
acceptance test antes da implementação principal. Altere apenas os paths
reservados, implemente a entrega real, execute gates atuais, corrija falhas e
produza uma demo reproduzível.

Classifique toda evidência como current, historical, not-run ou
environment-blocked. Não transforme fixture, healthcheck, ASGI local, código
IaC ou claim documental em pass hosted. Use apenas dados sintéticos.

Autorizado: edição local, testes, builds, Docker descartável, migrations
descartáveis e commits locais. Não autorizado sem checkpoint explícito:
provider pago, credencial, dado real, e-mail, holdout, usuário externo, push,
PR, tag, release, produção ou publicação.

Finalize com docs/handoffs/roadmap/<ID>-DONE.md contendo base e delivery SHA,
paths, comandos, resultados, skips, claims permitidas/proibidas, riscos,
rollback e próximo pacote. Termine com worktree sem resíduo da lane.
```

## 19. Checklist do roadmap manager

Este bloco é simultaneamente legível por pessoas e pelo parser da skill
`umcp-roadmap-manager`. Cada executor altera somente a própria linha de `[ ]`
para `[x]`, depois de satisfazer o gate, escrever o handoff e criar o commit
local. A caixa é uma claim de entrega; o manager ainda precisa reconciliar SHA,
árvore limpa, handoff e evidência antes de liberar dependências.

Sufixos `L`, `T` e `A` separam, respectivamente, lanes Luna, Terra e auditoria
que aparecem combinadas nas descrições acima. `checkpoint` remete à seção 17.

<!-- roadmap-manager:start -->
- [x] R00 | model=terra | depends=- | checkpoint=- | title=Criar candidato canônico M0 e M1
- [x] R01 | model=luna | depends=R00 | checkpoint=- | title=Integrar documentação e playbooks pós-M1
- [x] R02 | model=terra | depends=R00 | checkpoint=- | title=Integrar lanes locais válidas de M2 e M3
- [x] H01 | model=terra | depends=R01,R02 | checkpoint=- | title=Reconciliar decisão GCP e congelar arquitetura
- [x] H02 | model=terra | depends=H01 | checkpoint=- | title=Endurecer IaC e pipeline GCP
- [x] H03 | model=terra | depends=R02,H01 | checkpoint=- | title=Compor MCP Streamable HTTP hosted
- [x] H04 | model=terra | depends=H01,H03 | checkpoint=- | title=Implementar OAuth OIDC consentimento e revogação
- [x] H05 | model=luna | depends=H04 | checkpoint=- | title=Entregar login e consent UX
- [x] H06 | model=terra | depends=H01,H04 | checkpoint=- | title=Fechar tenancy RLS KMS e recuperação hosted
- [x] H07 | model=audit | depends=H02,H05,H06 | checkpoint=CP-1,CP-2,CP-3 | title=Integrar e auditar M2 em staging
- [x] C01 | model=luna | depends=H07 | checkpoint=- | title=Entregar runner comum e SDK Python
- [x] C02 | model=luna | depends=C01 | checkpoint=- | title=Comprovar primeiro conector real controlado
- [ ] C03 | model=luna | depends=C02 | checkpoint=CP-4 | title=Comprovar primeira superfície externa real
- [ ] C04 | model=luna | depends=C03 | checkpoint=CP-4 | title=Comprovar segunda superfície externa real
- [ ] C05L | model=luna | depends=C03,C04 | checkpoint=- | title=Entregar SDK TypeScript recipes e matriz M3
- [ ] C05A | model=audit | depends=C05L | checkpoint=- | title=Auditar Gate M3 e claims de conectores
- [ ] A01 | model=terra | depends=C05A | checkpoint=- | title=Entregar concepts domain e migrations
- [ ] A02 | model=terra | depends=A01 | checkpoint=- | title=Entregar jobs de consolidação
- [ ] A03 | model=luna | depends=H05,C05A,A01 | checkpoint=- | title=Conectar Inbox e Connections reais
- [ ] A04 | model=luna | depends=A01 | checkpoint=- | title=Entregar Concepts UI
- [ ] A05T | model=terra | depends=A01,A02 | checkpoint=- | title=Entregar domínio e APIs de Mental Notes e Activity
- [ ] A05L | model=luna | depends=A03,A04,A05T | checkpoint=- | title=Entregar UX de Mental Notes e Activity
- [ ] A05A | model=audit | depends=A05L | checkpoint=- | title=Auditar Gate M4 Memory Atlas
- [ ] T01 | model=terra | depends=A05A | checkpoint=- | title=Congelar governança e corpus development
- [ ] T02 | model=terra | depends=T01 | checkpoint=- | title=Validar capture policy dedupe e conflito
- [ ] T03 | model=terra | depends=T01,T02 | checkpoint=- | title=Validar recall abstention e segurança
- [ ] T04 | model=terra | depends=T02,T03 | checkpoint=- | title=Fechar workers desempenho e custo
- [ ] T05L | model=luna | depends=T02,T03,T04 | checkpoint=- | title=Entregar feedback UX e relatórios M5
- [ ] T05A | model=audit | depends=T05L | checkpoint=- | title=Auditar Gate M5 Trusted Recall
- [ ] B01 | model=luna | depends=T05A | checkpoint=- | title=Entregar onboarding e controles de usuário
- [ ] B02 | model=terra | depends=T05A | checkpoint=- | title=Entregar operação quotas e console
- [ ] B03 | model=terra | depends=B01,B02 | checkpoint=- | title=Executar drills e fechar beta readiness
- [ ] B04L | model=luna | depends=B03 | checkpoint=CP-6 | title=Abrir onboarding do private managed beta
- [ ] B04T | model=terra | depends=B04L | checkpoint=CP-6 | title=Operar e auditar o private managed beta
- [ ] O01 | model=terra | depends=B04T | checkpoint=- | title=Fechar clean install e artefatos Community após beta privado
- [ ] O02 | model=luna | depends=O01 | checkpoint=- | title=Entregar SDKs examples e documentação Community
- [ ] O03 | model=terra | depends=O01 | checkpoint=- | title=Fechar supply chain e CI
- [ ] O04 | model=audit | depends=O02,O03 | checkpoint=- | title=Executar auditoria independente M7
- [ ] G01L | model=luna | depends=B04T,O04 | checkpoint=CP-8 | title=Entregar experiência e comunicação de Public Beta
- [ ] G01T | model=terra | depends=G01L | checkpoint=CP-8 | title=Fechar operação e capacidade de Public Beta
- [ ] G02 | model=audit | depends=G01T | checkpoint=CP-5,CP-8 | title=Auditar candidato GA e holdout autorizado
- [ ] G03L | model=luna | depends=G02 | checkpoint=- | title=Preparar claims e release notes finais
- [ ] G03A | model=audit | depends=G03L | checkpoint=- | title=Produzir decisão humana final de lançamento
<!-- roadmap-manager:end -->

## 20. Definição final de entregue

O roadmap somente estará entregue quando:

- M0–M7 tiverem gates atuais no candidato canônico;
- M8 tiver decisão humana explícita correspondente ao estágio anunciado;
- dois clientes reais comprovados compartilharem o mesmo vault autorizado;
- captura, review, recall, provenance, correction, export, revoke e forget
  funcionarem end-to-end;
- cross-tenant leakage e category-policy violation forem zero nos gates;
- auth, RLS, crypto, backup, restore, delete e incident response tiverem
  auditoria atual;
- Community for reproduzível a partir de SHA limpo;
- claims públicas corresponderem literalmente às evidências;
- publicação ocorrer somente após autorização separada.

Até lá, o estado honesto do projeto é: **M2 staging-ready; SDK/agent M3
implementados com reauditoria de proveniência pendente; nenhuma superfície
externa, produção ou beta aberto.**
