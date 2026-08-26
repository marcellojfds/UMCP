# H07 — Promoção e Auditoria Operacional Staging (Resultado & Handoff)

## Resumo da Execução

Promovido e auditado o candidato H07 no serviço Cloud Run de Staging (`umcp-cloud-staging`). A suíte de validação local e os builds remotos foram concluídos com sucesso. No gate de verificação pós-deploy não-autenticada, o acesso público ao endpoint `/mcp` foi bloqueado pelo proxy IAM do Cloud Run (serviço não possui `--allow-unauthenticated`). Conforme a política de segurança e fail-closed do H07, o tráfego foi 100% revertido para a revisão estável `umcp-cloud-staging-00001-pjj`.

## Decisão Operacional
- **Resultado Final**: **NO-GO** (honesto, 9 dos 10 gates aprovados / 1 bloqueado por IAM público).
- **Ação de Rollback**: Executada e confirmada. 100% do tráfego servido pela revisão estável `umcp-cloud-staging-00001-pjj`.

---

## Parâmetros e Provenance da Promoção

- **Projeto GCP**: `umcp-mcp-staging-20260825`
- **Região GCP**: `us-central1`
- **Serviço Cloud Run**: `umcp-cloud-staging`
- **Identidade GCP**: `marcellojunqueirafds@gmail.com`
- **Commit Base (`SOURCE_SHA`)**: `705e68f5d658899c7e808af4f82326d2ba365b08`
- **Tag Imutável**: `southamerica-east1-docker.pkg.dev/umcp-mcp-staging-20260825/umcp-docker-repo/umcp:705e68f5d658899c7e808af4f82326d2ba365b08`
- **Digest Imutável (`IMAGE_DIGEST`)**: `sha256:ba8971fd7a43de4f719d759dd7c2343cdb095e2c26f454f06d8b6f45f9892ea3`
- **Revisão Candidata Criada**: `umcp-cloud-staging-00004-z9m`
- **Revisão de Rollback Restabelecida**: `umcp-cloud-staging-00001-pjj` (100% do tráfego)

---

## Correções e Remediações Entregues

1. **Seleção de Imagem Base Docker**:
   - Atualizado o `Dockerfile` para utilizar a imagem base `python:3.11-slim`, resolvendo o erro de digest ausente no Docker Hub.
2. **Inclusão da Pasta de Migrações no Build Wheel**:
   - Incluído `COPY migrations ./migrations` no `Dockerfile` para satisfazer a regra `force-include` do Hatchling em `pyproject.toml`.
3. **Inicialização do Runtime Fail-Closed em Staging**:
   - Definida a variável de ambiente `OMP_BACKEND=demo` no deploy do Cloud Run, permitindo a inicialização do runtime sem dependência de um banco PostgreSQL externo não configurado.
4. **Headers HTTP de Provenance**:
   - Injetados os headers `X-UMCP-Image-Digest` e `X-UMCP-Image-Source-SHA` nas respostas da aplicação FastAPI em `src/omp/server/official.py` e `src/omp/config.py`.

---

## Tabela de Auditoria dos 10 Gates H07

| # | Gate | Status | Descrição |
|---|---|---|---|
| 1 | GCP IaC Local & Pipeline Guardrails | `PASS` (`current`) | `./scripts/validate-gcp-local` aprovado sem ressalvas. |
| 2 | Verificação de Sintaxe dos Shell Scripts | `PASS` (`current`) | `sh -n` em todos os scripts shell aprovado. |
| 3 | Validação Unitária Offline do Verificador | `PASS` (`current`) | `scripts/test-verify-mcp-post-deploy.sh` aprovado. |
| 4 | Validação de Preflight Audit H07 | `PASS` (`current`) | `scripts/preflight-h07-audit.sh` aprovado com escopo e SHA estritos. |
| 5 | Git Diff & Branch Status | `PASS` (`current`) | `git diff --check` aprovado. |
| 6 | Submissão e Build Remoto (Cloud Build) | `PASS` (`current`) | Build `f966ad78-ab26-4a66-99f5-9829be0d6419` concluído (`SUCCESS`). |
| 7 | Contêiner & Readiness Check | `PASS` (`current`) | Aplicação iniciou e respondeu na porta 8080 com backend `demo`. |
| 8 | Implantação da Revisão Cloud Run | `PASS` (`current`) | Criada revisão `umcp-cloud-staging-00004-z9m` com rótulo `source_sha`. |
| 9 | Verificador Pós-Deploy Público (`verify-mcp-post-deploy.sh`) | `FAIL` (`environment-blocked`) | Bloqueado por política IAM de acesso não-autenticado do Cloud Run Staging. |
| 10 | Rollback e Preservação da Revisão Estável | `PASS` (`current`) | Tráfego revertido 100% para `umcp-cloud-staging-00001-pjj`. |

---

## Próximos Passos Recomendados

1. **Configuração de Autenticação OIDC / Service Account para Auditoria**:
   - Para que o script `verify-mcp-post-deploy.sh` possa validar requisições diretamente contra o Cloud Run em ambiente fechado, fornecer um token OIDC assinado para a audiência do Cloud Run ou configurar IAM permissivo temporário no ambiente de staging.
2. **Re-promoção do H07**:
   - Executar novamente a promoção com a credencial autorizada para liberação definitiva do gate 9.
