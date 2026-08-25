# M02–M08 — relatório de lacunas para adoção GCP

**Decisão desta auditoria:** os artefatos GCP locais são uma proposta de
infraestrutura de staging **não aceita**. Este relatório não autoriza M02, não
atesta recursos remotos e não executou comandos, APIs ou consultas externas.

## Escopo e regra de evidência

Foram inspecionados somente arquivos locais. “Observado” significa que a
configuração, código ou contrato correspondente está presente no checkout;
isso não prova que tenha sido aplicado, que o recurso exista, que uma política
remota esteja efetiva ou que um teste tenha passado. “Claim” significa uma
afirmação de documento sem evidência local executável suficiente para esta
auditoria. Ausência de configuração é uma lacuna, não prova de ausência remota.

| Fonte local | Estado que a auditoria pode afirmar | Claim que não é aceito como prova |
| --- | --- | --- |
| [`M02-GCP-DEPLOYMENT-DONE.md`](M02-GCP-DEPLOYMENT-DONE.md) | O arquivo declara `DONE / VERIFIED` e enumera URL, billing e probes. | Deploy, billing conciliado, URL alcançável e respostas HTTP: todos exigem verificação externa, que não foi feita. |
| [`gcp-deployment.md`](../../runbooks/gcp-deployment.md) | O runbook declara `ACTIVE / PRODUCTION-READY` e instruções de `curl`/deploy. | Que Cloud Run, Cloud SQL, KMS, Secret Manager ou Artifact Registry foram criados/configurados como descrito. |
| [`ops/terraform/gcp/`](../../../ops/terraform/gcp/) | Há código Terraform para APIs, Cloud Run, Cloud SQL, KMS, Secret Manager e Artifact Registry. | Que `terraform apply` foi executado, que há state revisado, ou que IAM/políticas remotas correspondem ao código. |
| [ADR 0010](../../adr/0010-mcp-streamable-http-and-admin-api.md), [ADR 0011](../../adr/0011-cloud-identity-authorization-and-consent.md), [ADR 0012](../../adr/0012-shared-postgres-rls-multitenancy.md) e [ADR 0013](../../adr/0013-server-decryptable-envelope-encryption.md) | São decisões/contratos de design para Cloud. ADR 0011 e 0013 dizem que seleção de IdP/KMS permanece pendente. | Implementação hosted, seleção de IdP/KMS, OAuth, RLS, criptografia por tenant ou readiness de produção. |
| [`cloud-principal-and-jobs-v1.md`](../../contracts/cloud-principal-and-jobs-v1.md) e [`cloud-migration-plan-v1.md`](../../contracts/cloud-migration-plan-v1.md) | Ambos se apresentam como contratos; o segundo diz explicitamente que migrations não estão autorizadas/aplicadas. | Principal verificado, worker assinado, migrations, RLS ou restore de Cloud em operação. |
| [`S05-privacy-ops-gate.md`](../alpha/S05-privacy-ops-gate.md) | Evidência local é limitada ao Alpha local/self-hosted e o próprio documento exclui hosted. | Qualquer gate de auth multi-tenant, Cloud backup/restore ou claim hosted. |

## Leitura dos artefatos GCP atuais: não aceitos

| Achado observado | Evidência local | Impacto / decisão |
| --- | --- | --- |
| Cloud Run é público. | [`cloud_run.tf`](../../../ops/terraform/gcp/cloud_run.tf) atribui `roles/run.invoker` a `allUsers`; o workflow usa `--allow-unauthenticated`. | **P0 blocker.** Expõe `/mcp` antes de gateway de identidade e consentimento. Remover acesso público antes de permitir tráfego; exceção só pode existir após desenho explícito de proxy/IAP/API gateway e testes de auth. |
| Não existe service account explícita no template Cloud Run nem bindings IAM de runtime/deployer. | O recurso `google_cloud_run_v2_service` não define `service_account`; não há recurso IAM em `ops/terraform/gcp/` além de invoker público. | **P0 blocker.** O deploy pode usar a default Compute Engine service account, excessivamente privilegiada conforme política de projeto. Exigir service accounts separadas, privilégio mínimo e prova de bindings antes de apply; confirmar o principal efetivo remotamente depois. |
| CI autentica com chave JSON estática. | [`.github/workflows/gcp-deploy.yml`](../../../.github/workflows/gcp-deploy.yml) passa `secrets.GCP_SA_KEY` a `credentials_json`, embora solicite `id-token: write`. | **P0 blocker.** Material de longa duração e sem escopo/proveniência demonstrados. Substituir por GitHub OIDC + Workload Identity Federation, atributo/repositório/branch restritos e SA de deploy dedicada; revogar/rotacionar a chave apenas sob procedimento aprovado. |
| Cloud SQL habilita IPv4 público e não há VPC, Private Service Access, connector ou proxy configurado. | [`cloud_sql.tf`](../../../ops/terraform/gcp/cloud_sql.tf) tem `ipv4_enabled = true`; não há recursos de rede no diretório. | **P0 blocker.** Viola o requisito de banco privado. Exigir IP privado, VPC dedicada, private service access e caminho Cloud Run→Cloud SQL privado/connector; bloquear authorized networks públicos. |
| A URL do banco no Cloud Run aponta a `localhost`, com senha interpolada, mas não há Cloud SQL volume/instance annotation, connector ou proxy. | [`cloud_run.tf`](../../../ops/terraform/gcp/cloud_run.tf) define `OMP_DATABASE_URL` em `localhost:5432`; não configura conexão Cloud SQL. | **P0 blocker funcional e de segredo.** A conectividade não é demonstrável pelo IaC e a senha gerada pode parar no Terraform state/plan. Usar integração privada suportada, runtime SA com `cloudsql.client`, e injeção de Secret Manager sem interpolar o valor em variável Terraform de runtime. |
| Secret Manager é criado, mas Cloud Run não referencia versões de segredo; JWT não aparece no runtime. | [`secret_manager.tf`](../../../ops/terraform/gcp/secret_manager.tf) cria dois segredos; [`cloud_run.tf`](../../../ops/terraform/gcp/cloud_run.tf) só usa a senha direta e KMS ID. | **P0 blocker.** “Secrets somente no Secret Manager” não está satisfeito. Definir contratos de consumo, IAM `secretAccessor` para a SA runtime, rotação e teste de indisponibilidade/redação. |
| KMS cria uma CryptoKey, mas não há IAM de uso, adapter/runtime de envelope encryption, auditoria de chave ou restore/rotação testados. | [`kms.tf`](../../../ops/terraform/gcp/kms.tf) só cria keyring/key; [`src/omp/config.py`](../../../src/omp/config.py) não possui configuração de KMS; [ADR 0013](../../adr/0013-server-decryptable-envelope-encryption.md) mantém provider pendente. | **P0 blocker de claim criptográfico.** Não declarar criptografia por tenant nem “at rest” até integração, falha fechada, rotação e restore em staging serem demonstrados. |
| Endpoint HTTP reutiliza adapter local. | [`composition.py`](../../../src/omp/server/composition.py) instancia `MCPAdapter(..., local_mode=True, transport="stdio")`; [`http.py`](../../../src/omp/server/http.py) apenas o monta em `/mcp`. | **P0 blocker.** Não há validação OIDC/OAuth, principal imutável, scopes, consentimento, revogação ou rejeição hosted comprovada. Exposição pública amplia o risco. |
| Backups/PITR são apenas flags de instância. | [`cloud_sql.tf`](../../../ops/terraform/gcp/cloud_sql.tf) habilita backup/PITR, sem retenção, inventário, procedimento de recuperação, tombstones ou teste; o contrato exige restore isolado e reaplicação de tombstones. | **P0 blocker de privacy/restore.** Backup configurado não é restore aceito. Sem restore isolado + replay de tombstones + RLS/chave, não liberar tráfego nem alegar deleção. |
| Observabilidade, alertas, budget/quotas, proteção de deploy e supply chain não são configurados. | Não há recursos locais para Logging/Monitoring, alert policies, dashboards, billing budget, quotas, WIF, state remoto ou políticas de imagem; o roadmap os requer. | **P1 blocker para beta/GA; P0 para um staged hosted que aceite dados.** Criar primeiro a base observável e os limites, com sinais redigidos. |
| O script mistura provisionamento, build e deploy, permite fallback imperativo e acesso não autenticado. | [`deploy-gcp.sh`](../../../scripts/deploy-gcp.sh) executa `terraform apply -auto-approve` ou `gcloud run deploy --allow-unauthenticated`. | **P1 blocker de controle de mudança.** Não é caminho de promoção auditável/reversível. Separar plan/aprovação/migrations/deploy/verification e remover fallback antes de uso. |

## O que GCP deve fornecer por marco

O mapa abaixo não substitui o roadmap de produto: somente explicita os
primitivos e evidências GCP que cada marco depende.

| Marco | Requisitos GCP mínimos | Gate de aceitação GCP | Rollback / no-go |
| --- | --- | --- | --- |
| **M02 — Identity & Hosted Alpha** | Projetos/ambientes separados; APIs habilitadas por IaC; service accounts distintas (runtime, migration, CI deploy) e IAM mínimo; Artifact Registry; Cloud Run privado com ingress controlado; VPC + Cloud SQL por IP privado; IdP selecionado após spike (Identity Platform só se atender OAuth/OIDC, magic link/Google login, JWKS e exportabilidade); Secret Manager + KMS; OAuth/OIDC; Cloud Logging/Monitoring redigidos; migrations explícitas; backup/restore; WIF para CI. | IdP e região/orçamento aprovados; endpoint HTTPS autenticado; token/PKCE/issuer/audience/scope/revogação e cross-tenant adversarial verdes; RLS e roles separadas; segredo não está em repo, env literal ou logs; migração zero→head/upgrade comprovada; restore isolado reaplica tombstones; alarmes básicos e orçamento criados. | Sem acesso público; parar rollout/reverter Cloud Run à revisão aprovada somente se compatível; migração de dados por forward-fix ou restore verificado, nunca downgrade destrutivo. Qualquer falha de auth/RLS/KMS/restore é no-go. |
| **M03 — Cross-client Connectors** | Cloud Run/gateway com OIDC discovery, JWKS e OAuth metadata; Identity Platform/IdP para consentimento e callbacks; Secret Manager para client credentials; WIF CI; Logging/Monitoring de auth sem token/PII; quotas/rate limiting na borda. | Dois clientes reais completam autorização, scopes e revogação em staging; logs não contêm bearer/cookie/e-mail/conteúdo; rate-limit e callbacks bloqueiam abuso. | Desabilitar cliente/redirect e revogar credenciais/consentimento; retirar revisão Cloud Run apenas após manter compatibilidade de tokens/migrations. |
| **M04 — Memory Atlas** | Cloud Run para API/admin separado; banco privado com RLS; Secret Manager/KMS conforme campos protegidos; Artifact Registry e WIF para releases; observabilidade por fluxo sem payload. | UI/admin acessa somente identidade/tenant autorizados; audit sem payload; isolamento continua verde após novos schemas e migrations. | Feature flags e revisão anterior da aplicação; forward-fix para schema; restore isolado se corrupção, seguido de reaplicação de tombstones. |
| **M05 — Trusted Recall** | Cloud Run workers/serviços separados e SAs dedicadas; conexão privada ao Cloud SQL; KMS/Secret Manager; fila/job com identidade assinada; Logging/Monitoring, métricas de latência/custo/fila, quotas e limites. | Budgets p50/p95/p99 e custo pré-definidos e observados; limites/backpressure/DLQ testados; worker falha fechado sem contexto tenant/KMS; nenhuma métrica/log vaza conteúdo. | Desativar feature/worker e drenar fila com jobs idempotentes; reverter aplicação sem desfazer dados; restore isolado se necessário. |
| **M06 — Closed Beta** | Projetos e chaves por ambiente; Cloud Monitoring/alertas/SLO, dashboards de custo/quotas por tenant, budget billing e alertas; backup/PITR com retenção inventariada; runbooks e canais de incidente; WIF CI/CD com promoção por revisão. | SLO observado, quotas e budget alertam, incident/restore/delete drills passam, rollout/rollback ensaiado, nenhuma P0/P1 aberta. | Pausar onboarding/feature flags, limitar revisões/instâncias, rollback à revisão aprovada e executar recuperação isolada; comunicar incidente conforme runbook. |
| **M07 — Open-source Release** | Artifact Registry e CI/CD com WIF; imagens imutáveis por digest, SBOM/proveniência/assinatura quando adotados; segregação de SAs e nenhum segredo em artefato; logs de deploy/auditoria. | Build reproduzível de SHA limpo, artefatos verificados e vinculados ao SHA; CI remoto/branch protection e scans comprovados. | Revogar/retirar artefato comprometido conforme processo de release; não apagar evidência/audit logs; publicar correção assinada. |
| **M08 — Public Beta/GA** | Capacidade/autoscaling/quotas aprovados, Monitoring/alerting/status, controles de abuso, backups/restore/delete em produção, WIF promotion, budgets e revisão IAM periódica. | SLO sustentado, auditoria auth/RLS/KMS, backup→restore→tombstone em produção, drills e claims aprovados; autorização humana explícita. | Congelar promoções, reduzir/fechar acesso público por borda, retornar a revisão estável e usar forward-fix/restore verificado; não declarar GA com controles apenas documentados. |

## Dependências e sequência de mudanças proposta

Nenhuma mudança abaixo foi implementada. Cada item depende da aceitação do
anterior e deve resultar em plan/revisão local antes de qualquer ação externa.

1. **Congelar e desqualificar a proposta atual.** Não executar o script ou
   workflow atuais; retirar `allUsers`/`--allow-unauthenticated` do plano de
   adoção e invalidar o claim de M02 pronto.
2. **Decisões humanas M02.** Aprovar projeto/ambiente, região e budget, IdP
   após spike autorizado, topologia de domínio/borda e proprietários de
   plataforma. Sem isso não há seleção legítima de Identity Platform/IdP ou
   provider KMS.
3. **Fundação de identidade GCP.** Criar desenho de SAs separadas, IAM mínimo,
   organização de projetos e Workload Identity Federation GitHub OIDC. Eliminar
   chave `GCP_SA_KEY` do caminho futuro, planejar rotação/revogação sob
   aprovação, e restringir deploy por repositório/branch/ambiente.
4. **Rede e dados privados.** Definir VPC, private service access, IP privado
   Cloud SQL, caminho Cloud Run/worker→DB, roles runtime/migration e state
   remoto protegido. Bloquear acesso público ao banco e confirmar que o
   connection mechanism não injeta segredo em state/env.
5. **Segredos e criptografia.** Modelar Secret Manager com versões, accessor
   por SA, rotação/redação; integrar KMS por adapter com fail-closed, auditoria
   e rotação. Só então configurar Cloud Run para referências de segredo, nunca
   valores interpolados.
6. **Aplicação e identidade hosted.** Implementar gateway que constrói
   `Principal` verificado, OAuth/OIDC/PKCE/consent/revogação e RLS/migrations
   contratuais; manter endpoint não público até a suite adversarial passar.
7. **Migração e recuperação.** Executar apenas migrations aditivas aprovadas;
   testar zero→head e upgrade; instituir backup inventariado, restore isolado,
   verificação de chave/RLS e reaplicação de tombstones antes de tráfego.
8. **Operação e promoção.** Instrumentação redigida, logging/monitoring,
   alertas, budget/quotas, probes sintéticos, Artifact Registry por digest e
   CI/CD WIF com plan/aprovação/migration/deploy/verification separados.
9. **Progressão de produto.** Abrir M02 somente ao atingir seu gate; os
   requisitos incrementais de M03–M08 entram após os gates anteriores, sem
   promover uma primitive de staging a claim de beta/GA.

## Bloqueadores de abertura e riscos residuais

| Prioridade | Bloqueador / risco | Condição objetiva para fechar |
| --- | --- | --- |
| P0 | `allUsers` e `--allow-unauthenticated` deixam o serviço público sem auth hosted. | Borda/Cloud Run inacessível sem identidade aprovada e testes de token/consent/scope/revogação verdes. |
| P0 | Ausência de SA explícita/IAM mínimo pode recorrer à default Compute Engine SA. | SAs runtime/migration/deploy explícitas, bindings mínimos revisados e identidade efetiva confirmada pós-apply. |
| P0 | `GCP_SA_KEY` é uma credencial estática em CI. | WIF GitHub OIDC com trust restrito e SA de deploy mínima; chave removida do fluxo e rotação/revogação aprovada. |
| P0 | Cloud SQL tem IPv4 e não há caminho privado Cloud Run→SQL. | VPC/PSA/IP privado/connector ou integração equivalente, sem rede pública autorizada, testado em staging. |
| P0 | Conexão `localhost` sem mecanismo Cloud SQL e senha interpolada em configuração Terraform. | Conexão privada comprovada, segredo referenciado no Secret Manager, sem valor secreto em env/state de runtime. |
| P0 | Não há OAuth/OIDC, principal verificado, RLS Cloud, KMS adapter, tombstones remotos ou restore aceito. | Contratos implementados e suites adversariais, KMS failure, backup/restore/tombstone em staging aprovadas. |
| P1 | Ausência de monitoring, alertas, quotas, budget, state remoto, políticas de imagem e runbooks de incidente Cloud. | Recursos/configuração e evidência operacional revisados antes de beta; para dados hosted, sinais mínimos antes do primeiro usuário. |
| P1 | Terraform permite `deletion_protection = false`; script faz `apply -auto-approve` e fallback imperativo. | Controle de mudança com plan/aprovação, proteção por ambiente, migração explícita e rollback documentado. |

## Gate de abertura da primeira onda GCP

Após aprovação deste plano, a primeira onda que pode ser aberta é a **fundação
M02 de segurança e landing zone**, limitada a decisões e desenho revisável:

- seleção humana de projeto/ambiente, região, orçamento e proprietário;
- arquitetura de IAM/service accounts e WIF (sem chave estática);
- arquitetura VPC/Cloud SQL privada e mecanismo de conexão;
- seleção do IdP via spike autorizado e contrato de OAuth/OIDC;
- matriz de segredos/KMS, logging/monitoring, quotas/budget e plano de
  migrations/restore.

Ela **não** inclui provisionamento, deploy, migração, abertura pública ou
aceitação de usuários. A próxima autorização deve exigir uma revisão do IaC
substituto e gates locais explícitos para cada dependência acima.

## Evidência local consultada

- [Roadmap de entrega](../../CODEX_DELIVERY_ROADMAP.md) — M02, M05–M08 e gates.
- [Gameplan productization](../../GAMEPLAN_PRODUCTIZATION_TERRA_LUNA.md) —
  requisitos de identity, RLS, crypto, operações e ondas.
- [Threat model hosted v1](../../threat-model-hosted-v1.md) — baseline de design,
  P0s e verificações obrigatórias.
- [Contrato de principal/jobs](../../contracts/cloud-principal-and-jobs-v1.md)
  e [plano de migration/recovery](../../contracts/cloud-migration-plan-v1.md).
- [IaC GCP](../../../ops/terraform/gcp/),
  [workflow de deploy](../../../.github/workflows/gcp-deploy.yml),
  [script de deploy](../../../scripts/deploy-gcp.sh) e
  [runtime HTTP](../../../src/omp/server/http.py).

Nenhum link acima é evidência de estado remoto; são apenas referências locais
para reprodução da inspeção.
