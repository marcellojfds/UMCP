# H07 — handoff operacional para AGY / OWL

## Missão

Promover e auditar **somente** o candidato H07 de staging, corrigindo o redirect HTTPS -> HTTP de `/mcp` e preservando provenance imagem -> SHA. O resultado aceitável é **GO** (dez gates H07 passam) ou **NO-GO** honesto, com rollback preservado. Não marque H07 sem todos os gates.

## Escopo autorizado

- Projeto: `umcp-mcp-staging-20260825`.
- Região: `us-central1`.
- Serviço Cloud Run: `umcp-cloud-staging`.
- Orçamento incremental máximo: US$10.
- Build/publish/deploy: somente a imagem candidata e uma nova revisão desse serviço; `cloudbuild.googleapis.com` já está habilitada.
- Rollback preservado: `umcp-cloud-staging-00001-pjj`.

Fora de escopo: produção, outros projetos/regiões, IAM/service accounts/WIF, Secret Manager, KMS, IdP/OAuth, banco/schema, dados ou usuários reais, e-mail, políticas de acesso, `--allow-unauthenticated`, push, PR, tag e release.

## Bloqueio atual

O build não chegou a iniciar: a identidade interativa disponível recebeu `PERMISSION_DENIED` em `gcloud builds submit`. Não há build ID, digest novo ou revisão nova. OWL deve usar uma sessão/identidade já autorizada para submeter Cloud Build, publicar no Artifact Registry existente e implantar apenas o serviço acima. Se isso não estiver disponível, interrompa antes de mudar IAM e registre o principal e a permissão faltante, sem expor tokens.

## Base e pacote obrigatório

Comece de um checkout limpo, destacado em:

```sh
git checkout --detach 9bd105d535a30ccbbf72a2d31d54327ee90f5196
git cherry-pick fd19644 191d9b6 fe4ee2a 1af644d 0419682 3d69c44
```

Os seis commits são obrigatórios e ordenados. Não inclua commits históricos de handoff/auditoria. Registre o SHA novo gerado pelos cherry-picks como `SOURCE_SHA`; ele é o valor de provenance da promoção.

## Validação local obrigatória

```sh
./scripts/validate-gcp-local
sh -n scripts/deploy-gcp.sh scripts/verify-mcp-post-deploy.sh scripts/preflight-h07-audit.sh scripts/test-verify-mcp-post-deploy.sh scripts/test-preflight-h07-audit.sh
scripts/test-verify-mcp-post-deploy.sh
scripts/test-preflight-h07-audit.sh
git diff --check
git status --short --branch
```

Falha nesses checks é NO-GO; não contorne com relaxamento de TLS, redirect ou provenance.

## Sequência remota permitida

1. Confirmar projeto, região, serviço, revisão de rollback e identidade ativa.
2. Submeter build com tag imutável baseada no `SOURCE_SHA`, publicando somente em `southamerica-east1-docker.pkg.dev/umcp-mcp-staging-20260825/umcp-docker-repo/umcp`.
3. Resolver o digest imutável resultante (`IMAGE_DIGEST`).
4. Executar o preflight em modo read-only, com endpoint HTTPS exato `/mcp`, serviço, revisão, digest e SHA reais; nunca passe segredos na linha de comando.
5. Implantar uma nova revisão do serviço existente com o par imutável `IMAGE_DIGEST` + `SOURCE_SHA`, sem mudar a política de acesso.
6. Confirmar que a nova revisão recebe tráfego e preserva `umcp-cloud-staging-00001-pjj` para rollback.
7. Rodar `scripts/verify-mcp-post-deploy.sh` contra o host allowlisted, endpoint HTTPS `/mcp` exato, digest e SHA esperados. Redirect, HTTP, ausência/divergência de headers ou qualquer gate falho é NO-GO.
8. Se falhar após mudança de tráfego, restaurar tráfego para `umcp-cloud-staging-00001-pjj`, coletar evidência e parar.

## Evidência de retorno exigida ao manager

- Identidade utilizada (redigida quando necessário), projeto/região/serviço.
- SHA do checkout, tag e digest imutável publicado.
- Nome da nova revisão e distribuição de tráfego.
- Saída redigida dos checks locais, preflight e verificador pós-deploy.
- Resultado de cada um dos dez gates H07, distinguindo `current`, `historical`, `not-run` e `environment-blocked`.
- Custo observado/estimado contra o teto de US$10.
- Ação de rollback, se houver.
- Decisão final GO/NO-GO. Somente GO com os dez gates atuais permite marcar H07.

## Estado anterior para comparação

- Endpoint anterior: `https://umcp-cloud-staging-yqjlathj7q-uc.a.run.app`.
- Revisão anterior/rollback: `umcp-cloud-staging-00001-pjj` (100% do tráfego).
- Digest anterior: `sha256:f5a34bda6e73d4a8a41ef1d8da1f62fa631ba92233a80cc72f15174bec08152a`.
- Falha observada: `/mcp` respondia 307 redirecionando HTTPS para HTTP.

Não exponha credenciais, tokens, segredos ou conteúdo de IAM no retorno.
