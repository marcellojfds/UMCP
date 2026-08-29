# C02 — Relatório de Execução do Controlled Python Agent

- **Data:** 2026-08-29T19:16:57.776634Z
- **Audit Cycle ID:** `audit-20260829191427-3d666ba5`
- **Base URL Staging:** `https://umcp-cloud-staging-yqjlathj7q-uc.a.run.app`
- **Audit Source SHA:** `74b4e7e46a14984e82a9fd4a0f1fa511ef074f42`
- **Server Source SHA:** `367cd365df43f9282f5155394cd39275169bf8f2`
- **Server Image Digest:** `sha256:764263db4907ffbbbd50e77ab7d12e8d88cde2b5990a9879a40ddbd0976e4f1d`
- **Server Active Revision:** `umcp-cloud-staging-00018-f78`
- **Audit Image Digest:** `sha256:6a5b8b0e95048c9b5c5f74a9d8452d0eb9ab3bb74db19e4e8aee3147b1c25124`
- **Job Execution:** `umcp-c01c02-audit-4273d666ba5-pmfnr`
- **Report ID:** `c02-e1ac6288ab58`
- **Canonical JSON Artifact:** [`C02-CONTROLLED-AGENT-REPORT-20260828.json`](./C02-CONTROLLED-AGENT-REPORT-20260828.json)
- **Checksum do Payload Canônico (SHA-256):** `sha256:677b8c552eff51c463aeb3932972f9c6478b4c6aa6051cc77f7abddaa0127b5f`
- **Checksum do Arquivo JSON (SHA-256):** `sha256:cffff6865b1e6ea9803cdc8ebc6b82a4c5d1880f28842671e88a27081cdad0b0`

## Classificação de credencial

O agente usou tokens sintéticos pré-provisionados; o passo `2_oauth_pkce_login` não é evidência de login interativo real.
A negação cross-tenant foi explícita na borda da aplicação; esta rodada não declara prova direta de RLS.

## Jornada C02

| Passo | Status |
| --- | --- |
| `1_discovery` | **PASS** |
| `2_oauth_pkce_login` | **PASS** |
| `3_mcp_initialize` | **PASS** |
| `4_mcp_tools_list` | **PASS** |
| `5_synthetic_write` | **PASS** |
| `6_recall_search` | **PASS** |
| `7_update` | **PASS** |
| `8_forget` | **PASS** |
| `9_tombstone_non_resurrection` | **PASS** |
| `10_provenance_preservation` | **PASS** |
| `11_refresh_rotation` | **PASS** |
| `12_token_revocation` | **PASS** |
| `13_unauthorized_after_revoke` | **PASS** |
| `14_forged_authority_rejection` | **PASS** |
| `15_tenant_isolation` | **PASS** |

## Negativos

- `unauthenticated_mcp_401`: **PASS**
- `authorization_code_replay_rejected`: **PASS**
- `old_refresh_rejected`: **PASS**
- `revoked_access_rejected_401`: **PASS**
- `forged_authority_explicit_rejection`: **PASS**
- `cross_tenant_explicit_rejection`: **PASS**
- `tombstone_non_resurrection`: **PASS**
