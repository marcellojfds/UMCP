# C02 — Relatório de Execução do Controlled Python Agent

- **Data:** 2026-08-29T14:06:59.609578Z
- **Versão do Agente:** `1.0.0`
- **Versão do SDK:** `1.0.0`
- **Base URL Staging:** `https://umcp-cloud-staging-yqjlathj7q-uc.a.run.app`
- **Audit Source SHA:** `72b9fad4d9ed6b54f44150d19fc3d3edef67e1ab`
- **Server Source SHA:** `367cd365df43f9282f5155394cd39275169bf8f2`
- **Server Image Digest:** `sha256:764263db4907ffbbbd50e77ab7d12e8d88cde2b5990a9879a40ddbd0976e4f1d`
- **Server Active Revision:** `umcp-cloud-staging-00018-f78`
- **Audit Image Digest:** `sha256:c39b3d02785b0a4f817da4074136b4d662c49085499e6cebbf8a69b96ccbedea`
- **Report ID:** `c02-e71fe8188a36`
- **Canonical JSON Artifact:** [`C02-CONTROLLED-AGENT-REPORT-20260828.json`](./C02-CONTROLLED-AGENT-REPORT-20260828.json)
- **Checksum do Payload Canônico (SHA-256):** `sha256:2e640048bb8430f27b77cc3977d3987017e0c7f6da145d1aa779ea458188f348`
- **Checksum do Arquivo JSON (SHA-256):** `sha256:560359cc3bc139c4f718378c960886a2416c1f3bfe398391e3b758835b438768`

---

## 1. Resultados dos 15 Passos da Jornada

| # | Passo | Status |
| :-: | :--- | :---: |
| `1_discovery` | `1_discovery` | **PASS** |
| `2_oauth_pkce_login` | `2_oauth_pkce_login` | **PASS** |
| `3_mcp_initialize` | `3_mcp_initialize` | **PASS** |
| `4_mcp_tools_list` | `4_mcp_tools_list` | **PASS** |
| `5_synthetic_write` | `5_synthetic_write` | **PASS** |
| `6_recall_search` | `6_recall_search` | **PASS** |
| `7_update` | `7_update` | **PASS** |
| `10_provenance_preservation` | `10_provenance_preservation` | **PASS** |
| `14_forged_authority_rejection` | `14_forged_authority_rejection` | **PASS** |
| `15_tenant_isolation` | `15_tenant_isolation` | **PASS** |
| `8_forget` | `8_forget` | **PASS** |
| `9_tombstone_non_resurrection` | `9_tombstone_non_resurrection` | **PASS** |
| `11_refresh_rotation` | `11_refresh_rotation` | **PASS** |
| `12_token_revocation` | `12_token_revocation` | **PASS** |
| `13_unauthorized_after_revoke` | `13_unauthorized_after_revoke` | **PASS** |

---

## 2. Resumo da Execução

- **Total de Passos:** 15
- **Passos Aprovados:** 15
- **Passos Falhos:** 0
- **Zero Mocks no Relatório Real:** Sim
- **Zero Segredos / Dados Pessoais:** Sim
