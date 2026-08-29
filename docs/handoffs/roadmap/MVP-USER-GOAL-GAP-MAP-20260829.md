---
title: MVP user-goal gap map — MCP, account UI, and cross-assistant transfer
status: planning-current
date: 2026-08-29
work_item: W04
base_sha: a9e7b5deefeb0f43799e95a09a263bea5a5757d6
scope: documentation-only
---

# W04 — mapa de lacunas dos resultados do usuário

## Escopo e aceitação congelada

Este é um mapa de planejamento; não implementa produto, não altera o checklist
canônico e não promove nenhum pacote a concluído. Antes desta redação, a
aceitação de W04 foi congelada como:

1. relacionar cada resultado a pacotes existentes e ao estado de evidência;
2. separar lacunas de produto de evidência histórica ou de autorização;
3. mostrar um caminho crítico com checkpoints humanos; e
4. definir testes E2E observáveis, usando somente dados sintéticos e sem
   tratar fixture, healthcheck ou documentação como prova hosted.

**Fontes lidas:** `coordination/SLACK-MANAGER-BOARD.md`,
`docs/handoffs/roadmap/MVP-RESUMPTION-20260829.md`,
`docs/roadmap_implementation.md` e
`docs/EXECUTION_RELIABILITY_PLAYBOOK.md`. Os handoffs, SHAs testados e
evidência de aceitação prevalecem sobre o mural de coordenação.

## Estado de partida que limita os três resultados

- H07 é `M02 STAGING READY`, na revisão
  `umcp-cloud-staging-00018-f78`; não é produção nem beta aberto.
- C01 (14/14) e C02 (15/15, contenção 0/0/0) têm implementação e reports
  úteis, mas seus gates estão **abertos**: a imagem de auditoria não foi
  construída de um `audit_source_sha` reproduzível. Nenhum resultado externo
  de M3 pode ser aceito antes da reexecução limpa.
- C03, C04 e C05 ainda não foram executados. A conexão de um agente controlado
  não conta como ChatGPT ou Gemini reais.
- O pacote H05 cobre login, consentimento e `/connections`, porém o handoff de
  retomada registra que ainda não há landing/dashboard hospedados. Portanto,
  não há evidência atual suficiente para afirmar que uma pessoa consegue
  acessar uma tela hospedada de gestão de contas depois de conectar um cliente.

## Mapa por resultado

| Resultado do usuário | Pacotes existentes que o cobrem | O que ainda não está provado / faltando | Condição de aceitação honesta |
| --- | --- | --- | --- |
| Conectar o MCP ao ChatGPT e ao Gemini | H03 (endpoint MCP), H04 (OAuth/OIDC, PKCE e scopes), H06 (isolamento), H07 (staging); C01/C02 (runner e agente controlado); C03 (primeira superfície externa, prioridade ChatGPT); C04 (segunda superfície externa); C05L/C05A (matriz e auditoria M3). | Fechar proveniência C01/C02; preflight oficial, datado, de capacidades e passos de cada superfície; CP-4; execução real de ChatGPT e Gemini com recipes limpas, reports checksummed e matriz. | ChatGPT e Gemini, cada qual em execução real autorizada, completam discovery, OAuth/consentimento, `initialize`, `tools/list` e uma chamada com scope mínimo; cada conector tem versão/data/report e pode ser revogado. |
| Tela hospedada de autenticação e gestão de contas | H04 cria a base de identidade, consentimento, conexão, rotação e revogação; H05 especifica `/login`, callback, consentimento e `/connections`; H07 inclui login e duas conexões no gate M2; A03 torna Inbox/Connections reais; B01 acrescenta onboarding, scopes, revoke, export/delete e controles de usuário. | Não há gate M3 que comprove a jornada web hospedada pós-conexão como uma unidade. A ausência declarada de landing/dashboard hospedados impede afirmar disponibilidade atual. Falta definir a rota/host permitido, retorno pós-autorização, estado de conexão, tratamento de expiração/erro, e o vínculo verificável entre revogar na UI e bloquear o cliente. | Uma sessão server-side entra em `/login`, dá consentimento, chega a `/connections` no host autorizado, vê somente metadados audit-safe (cliente, scopes, estado e last-used), e uma revogação ali bloqueia apenas a conexão correspondente no cliente real. |
| Transferir uma memória/conversa entre assistants por MCP | O modelo de vault compartilhado é coberto por C03/C04/C05: A registra e B recupera, atualiza, esquece e revoga. M1 e os contratos internos já descrevem export/import owner-scoped, validação, idempotência e tombstone blocking; H04 reserva `memory:export`; B01 prevê controles de export/delete. | **Lacuna de produto:** C03/C04 exigem cross-client recall no mesmo vault, não um export/import portátil exposto e consumível via MCP. O export/import existente é administrativo/transport-neutral ou sintético; não há pacote M3 que congele formato, autorização reforçada, provenance, importação, idempotência, limites e recipe para um segundo assistant. B01 está depois de M5 e, sozinho, é tarde demais para satisfazer este resultado do MVP. | Após os dois conectores reais, A solicita exportação autorizada de dado sintético; o bundle versionado e redigido é validado/importado por B via MCP, preserva provenance e lifecycle, não duplica reimportação, não ressuscita tombstone e deixa tenant B com zero resultados. |

## Tarefas faltantes propostas (não inseridas no checklist)

Estas são lacunas para decisão do manager; os identificadores são locais a
este mapa e **não** são novas linhas do roadmap.

| ID proposto | Posicionamento | Entrega mínima e gate |
| --- | --- | --- |
| GAP-C03-01 — preflight por superfície | Antes de C03 e novamente antes de C04. | Matriz oficial, datada, para ChatGPT e Gemini: disponibilidade MCP, UI/fluxo de conexão, OAuth/redirect/scopes, limitações de import/export e ações exatas do owner. Não transforma documentação em suporte; alimenta a decisão CP-4. W03 é a evidência de planejamento inicial, não a execução. |
| GAP-UI-01 — jornada hospedada pós-conexão | Depois de C03, antes de aceitar o resultado de gestão de contas; pode usar H04/H05 sem reabrir H07. | Congelar uma acceptance E2E para `/login` → consentimento → callback → `/connections`, com estados de loading/denied/expired/revoked e revoke real. Exigir host/rota publicados apenas sob autorização aplicável e sem token, e-mail ou conteúdo nos logs. |
| GAP-XFER-01 — contrato portátil MCP | Depois de C04 e antes de C05A. | Especificar versão do bundle, ferramentas/recursos MCP de exportação e importação, scope `memory:export`, reautenticação/confirmação, limites, validação, idempotência, provenance, erro seguro e política de incompatibilidade. Não expor export administrativo como ferramenta de cliente sem essa fronteira. |
| GAP-XFER-02 — recipe e relatório cross-assistant | Depois de GAP-XFER-01; requisito adicional ao report C05. | Executar A→B com dados sintéticos em ChatGPT e Gemini reais, e B→A quando suportado; conferir checksum do report, reimportação, forget/tombstone, revoke e isolamento. A support matrix só eleva a capacidade comprovada. |
| GAP-OPS-01 — prontidão mínima para tela e transferência | Antes de qualquer teste com pessoa externa; B01/B02/B03 permanecem os pacotes completos posteriores. | Definir owner de suporte, quota/kill switch e procedimento de revogação/rollback para a demonstração autorizada. Sem CP-6, o resultado pode ser demonstrado de forma controlada, mas nunca é beta aberto. |

## Caminho crítico até os três resultados

```text
C01/C02: reauditoria de SHA limpo (14/14 + 15/15 + 0/0/0)
  → GAP-C03-01: capability preflight atual
  → CP-4: owner autoriza clientes, credenciais, endpoint e uso
  → C03: ChatGPT real + report
  → GAP-UI-01: jornada hospedada login/connections/revoke E2E
  → C04: Gemini real + report
  → GAP-XFER-01: contrato de transferência MCP
  → GAP-XFER-02: transferência ChatGPT ↔ Gemini E2E
  → C05L/C05A: matriz, recipes e auditoria M3
```

H04/H05/H06/H07 são predecessores já declarados e não devem ser reabertos por
este mapa. A03 e B01 melhoram a experiência/controles, mas não ficam no caminho
mínimo da demonstração controlada; B01–B04 e CP-6 são obrigatórios antes de
transformar a demonstração em private managed beta.

## Checkpoints e limites de autorização

| Checkpoint | Quando é necessário | Decisão que não pode ser inferida |
| --- | --- | --- |
| CP-4 | Antes de C03/C04 ou de qualquer conexão real ChatGPT/Gemini. | Credenciais/client registration, endpoint, escopos, redirect URIs e uso autorizado dos serviços. |
| CP-2 / CP-3 | Somente se a lacuna exigir mudar IdP, callback, segredo, KMS ou IAM. | Provider, e-mail/callback, owners, rotação e revogação. H07 prévio não autoriza mudança nova. |
| CP-6 | Antes de convidar usuários ou tratar a jornada como beta. | Coorte consentida, suporte, quotas, canal de incidentes e kill switch. |

Nenhum checkpoint autoriza push, PR, tag, release, produção, usuários externos,
dados reais ou publicação. Falta de autorização é `blocked`, não um convite a
simular o passo externo.

## Checkpoints de aceitação E2E

Cada cenário deve ser executado no SHA/digest candidato, com dados sintéticos,
report datado e checksummed; logs e artefatos não podem conter bearer token,
cookie, e-mail ou conteúdo de memória.

| ID | Cenário observável | Passa somente se |
| --- | --- | --- |
| E2E-0 | Reexecutar C01/C02 a partir de commit limpo. | `audit_source_sha` coincide exatamente com a fonte da imagem; C01 14/14, C02 15/15 e contenção 0/0/0 na mesma rodada. |
| E2E-1 | Conexão ChatGPT real (C03). | Discovery, PKCE/consentimento, MCP `initialize`/`tools/list`/chamada scoped, report checksummed e revoke com erro seguro ocorrem no cliente real. |
| E2E-2 | Tela de conta após conexão. | Sessão server-side mostra somente a conexão autorizada e seus scopes; estados denied/expired/revoked são claros; revogar na UI bloqueia A sem afetar uma conexão B válida do mesmo usuário. |
| E2E-3 | Conexão Gemini real (C04). | Repete E2E-1 em superfície distinta; a matriz registra versão/data e não chama capacidade não testada de `Supported`. |
| E2E-4 | Vault compartilhado A→B e controles. | ChatGPT captura uma memória sintética com provenance; Gemini recupera, atualiza com versão esperada e esquece; tenant B não lê nada; revogar A não revoga B. Executar o sentido inverso quando a superfície o suportar. |
| E2E-5 | Transferência portátil via MCP. | A exporta sob scope e confirmação apropriados; B importa bundle válido sem duplicar replay, preserva provenance/lifecycle, rejeita bundle inválido e não restaura conteúdo tombstoned. |
| E2E-6 | Negativos transversais. | Token expirado/revogado, scope ausente, owner/tenant forjado, callback indevido e cliente não autorizado falham antes do serviço/banco e sem vazamento. |

## Estado que este handoff permite declarar

- Existe uma rota planejada para os três resultados, mas nenhum dos três está
  aceito hoje como jornada externa atual.
- A demonstração mínima depende primeiro do fechamento reproduzível de C01/C02
  e de CP-4; depois exige ChatGPT e Gemini reais, não simuladores.
- Shared-vault cross-assistant é coberto pela direção C03/C04, enquanto
  transferência portável export/import via MCP requer as lacunas GAP-XFER-01 e
  GAP-XFER-02 antes de qualquer claim de resultado completo.

## Evidência de W04 e próximo passo

| Gate | SHA | Freshness | Resultado | Artefato |
| --- | --- | --- | --- | --- |
| Leitura das quatro fontes mandatórias e preflight Git | `a9e7b5deefeb0f43799e95a09a263bea5a5757d6` | current | pass | este handoff e `git worktree list` da sessão W04 |
| Teste de produto/MCP | — | not-run | não aplicável a W04 documental | nenhum; este pacote não alterou runtime |
| Aceitação dos resultados do usuário | — | not-run | pendente dos E2E acima | C01–C05 + lacunas propostas |

**Próximo passo:** o manager deve reconciliar W04 e manter C01/C02 como o
bloqueador imediato. Após a reauditoria, usar o preflight W03 e buscar a
decisão CP-4 antes de iniciar C03; não marcar qualquer checklist a partir deste
documento.
