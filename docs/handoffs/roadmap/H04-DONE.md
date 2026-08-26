# H04 handoff — OAuth/OIDC, consentimento e revogação

## Estado

`DONE — contrato local sintético / fail-closed`. Esta entrega não configura
IdP, cliente, redirect URI real, e-mail, credencial, provider, deploy ou
serviço externo. Não é hosted, staging ou produção.

## Base e paths

- Base canônica: `e1bdc9b82a8f80c37a766376ad1d13186bdbe766` (H03).
- Paths alterados: `src/omp/server/identity_contracts.py`,
  `tests/unit/test_h04_identity_contracts.py`, este handoff e somente a linha
  H04 do checklist.
- Dados: exclusivamente UUIDs, URLs `.example.test`, escopos e tokens
  sintéticos de teste.

## Entrega e evidência

Foram congelados contratos/interfaces para metadata de protected resource e
authorization server, authorization code + PKCE S256, allowlist de callback,
consentimento versionado e binding de conexão. O fluxo sintético rejeita
redirect não permitido, PKCE ausente/incorreto, consent mismatch e code
reutilizado. Revogação bloqueia credential e connection, com evento seguro.

O `Principal` continua imutável e derivado apenas de `VerifiedCredential` já
validado pelo `CredentialVerifier`; H03 e o seam interno `/_hosted_boundary`
foram preservados. Nenhum request inválido chega ao serviço nos testes
existentes de auth/gateway, incluindo credencial ausente/expirada,
issuer/audience errados, scope insuficiente e campos `owner_id`/`tenant_id`
forjados.

## Comandos e resultados

- `ruff check src/omp/server/identity_contracts.py tests/unit/test_h04_identity_contracts.py` — PASS.
- `pytest -q tests/unit/test_h04_identity_contracts.py tests/unit/test_hosted_auth.py tests/contract/test_hosted_gateway.py tests/contract/test_h03_streamable_http.py tests/conformance/test_m03_connector_contract.py tests/conformance/test_m03_connector_recipe.py` — PASS, 24 testes.
- Suite adicional incluindo `tests/conformance/test_m1_portable_memory.py` — 24 PASS, 1 FAIL por endpoint HTTP M1 indisponível no ambiente (`M1HarnessError: initialize`); classificado `environment-blocked`, não convertido em pass.
- `mypy src/omp/server/identity_contracts.py` — o arquivo H04 passa; a execução global reporta três erros preexistentes fora dos paths H04 em `src/omp/application/services.py` e `src/omp/adapters/postgres/repository.py`.

## Skips, claims e bloqueios

Não foram executados IdP/JWKS reais, registro de cliente, callback externo,
OAuth hosted, browser E2E, deploy, staging ou serviços externos; CP-2 não é
necessário para este contrato local e permanece obrigatório para qualquer
integração real. Claim permitido: contrato e fluxos sintéticos locais
fail-closed. Claims proibidos: OAuth/OIDC operacional, provider configurado,
login hosted, staging, produção ou segurança operacional comprovada.

## Rollback

Reverter o commit desta lane remove `identity_contracts.py`, seu teste, este
handoff e a marca H04; H03 permanece no SHA-base.

## Próximos bloqueios

H05 pode consumir o contrato congelado localmente. Qualquer seleção de IdP,
registro de cliente, redirect URI ou credencial exige CP-2; secrets/KMS/IAM
externos exigem CP-3.
