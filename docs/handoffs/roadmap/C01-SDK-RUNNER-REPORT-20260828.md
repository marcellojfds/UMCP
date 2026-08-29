# C01 — Relatório de Conformance do SDK Python e Runner Comum

- **Data:** 2026-08-29T13:21:50.298664Z
- **Versão do SDK:** `1.0.0`
- **Protocolo:** `omp.mcp.v0`
- **Base URL Staging:** `https://umcp-cloud-staging-yqjlathj7q-uc.a.run.app`
- **Server Source SHA:** `96f5391a61801469e3cdbe1ec249689f6f7b00de`
- **Server Image Digest:** `sha256:764263db4907ffbbbd50e77ab7d12e8d88cde2b5990a9879a40ddbd0976e4f1d`
- **Server Active Revision:** `umcp-cloud-staging-00018-f78`
- **Report ID:** `c01-1b8ae7c74738`
- **Canonical JSON Artifact:** [`C01-SDK-RUNNER-REPORT-20260828.json`](./C01-SDK-RUNNER-REPORT-20260828.json)
- **Checksum do Payload Canônico (SHA-256):** `sha256:6a146b196dd036fc8661d5007ca556cf9fa4239a30d69f36e6e603c93ad59125`
- **Checksum do Arquivo JSON (SHA-256):** `sha256:5cf047e847cc275df8d86965a1b00d9f61284e005ca2106e9c638fc945b5a005`

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
