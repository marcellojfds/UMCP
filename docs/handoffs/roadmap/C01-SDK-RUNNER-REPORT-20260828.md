# C01 — Relatório de Conformance do SDK Python e Runner Comum

- **Data:** 2026-08-29T11:54:07.402918Z
- **Versão do SDK:** `1.0.0`
- **Protocolo:** `omp.mcp.v0`
- **Base URL Staging:** `https://umcp-cloud-staging-yqjlathj7q-uc.a.run.app`
- **Server Source SHA:** `367cd365df43f9282f5155394cd39275169bf8f2`
- **Server Image Digest:** `sha256:764263db4907ffbbbd50e77ab7d12e8d88cde2b5990a9879a40ddbd0976e4f1d`
- **Server Active Revision:** `umcp-cloud-staging-00018-f78`
- **Report ID:** `c01-61b067ce8e1c`
- **Canonical JSON Artifact:** [`C01-SDK-RUNNER-REPORT-20260828.json`](./C01-SDK-RUNNER-REPORT-20260828.json)
- **Checksum do Payload Canônico (SHA-256):** `sha256:6089bbd28d8deae740450a6c5ada748382565297c257052c28090ce081f0e53e`
- **Checksum do Arquivo JSON (SHA-256):** `sha256:e7771a06fe00fdc6122952997b52a31926d6790d4d70b887a1a43f3c17ab781f`

---

## 1. Escopos Autorizados

- `memory:read`
- `memory:write`
- `memory:delete`

---

## 2. Matriz de Conformance (Derivada de Resultados Reais)

| Capacidade | Status |
| :--- | :---: |
| `protected_resource_discovery` | **Supported** |
| `authorization_server_discovery` | **Supported** |
| `oauth_pkce_s256` | **Supported** |
| `token_exchange` | **Supported** |
| `mcp_initialize` | **Supported** |
| `mcp_tools_list` | **Supported** |
| `memory_write_synthetic` | **Supported** |
| `memory_search_synthetic` | **Supported** |
| `memory_update_synthetic` | **Supported** |
| `memory_forget_synthetic` | **Supported** |
| `token_refresh_rotation` | **Supported** |
| `token_revocation` | **Supported** |
| `forged_authority_rejection` | **Supported** |
| `zero_leakage_redaction` | **Supported** |

---

## 3. Resumo da Verificação

- **Total de Capacidades:** 14
- **Suportadas e Validadas:** 14
- **Não Verificadas / Pendentes:** 0
- **Zero Mocks no Relatório Real:** Sim
- **Zero Segredos / Dados Pessoais:** Sim
