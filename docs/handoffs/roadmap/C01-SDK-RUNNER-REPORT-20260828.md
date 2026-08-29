# C01 — Relatório de Conformance do SDK Python e Runner Comum

- **Data:** 2026-08-29T14:07:05.108478Z
- **Versão do SDK:** `1.0.0`
- **Protocolo:** `omp.mcp.v0`
- **Base URL Staging:** `https://umcp-cloud-staging-yqjlathj7q-uc.a.run.app`
- **Audit Source SHA:** `72b9fad4d9ed6b54f44150d19fc3d3edef67e1ab`
- **Server Source SHA:** `367cd365df43f9282f5155394cd39275169bf8f2`
- **Server Image Digest:** `sha256:764263db4907ffbbbd50e77ab7d12e8d88cde2b5990a9879a40ddbd0976e4f1d`
- **Server Active Revision:** `umcp-cloud-staging-00018-f78`
- **Audit Image Digest:** `sha256:c39b3d02785b0a4f817da4074136b4d662c49085499e6cebbf8a69b96ccbedea`
- **Report ID:** `c01-3894497a69e4`
- **Canonical JSON Artifact:** [`C01-SDK-RUNNER-REPORT-20260828.json`](./C01-SDK-RUNNER-REPORT-20260828.json)
- **Checksum do Payload Canônico (SHA-256):** `sha256:a85b2ea0ee5fa0b34259c95b28073d336efa3f81d8e6fd224417ab86ece0a1a5`
- **Checksum do Arquivo JSON (SHA-256):** `sha256:51c48a53ebeb3de19c2c2a83669762bbf278a358a975480b9914a65b05b853ba`

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
