# C01 — Relatório de Conformance do SDK Python e Runner Comum

- **Data:** 2026-08-29T19:17:01.129355Z
- **Audit Cycle ID:** `audit-20260829191427-3d666ba5`
- **Base URL Staging:** `https://umcp-cloud-staging-yqjlathj7q-uc.a.run.app`
- **Audit Source SHA:** `74b4e7e46a14984e82a9fd4a0f1fa511ef074f42`
- **Server Source SHA:** `367cd365df43f9282f5155394cd39275169bf8f2`
- **Server Image Digest:** `sha256:764263db4907ffbbbd50e77ab7d12e8d88cde2b5990a9879a40ddbd0976e4f1d`
- **Server Active Revision:** `umcp-cloud-staging-00018-f78`
- **Audit Image Digest:** `sha256:6a5b8b0e95048c9b5c5f74a9d8452d0eb9ab3bb74db19e4e8aee3147b1c25124`
- **Job Execution:** `umcp-c01c02-audit-4273d666ba5-pmfnr`
- **Report ID:** `c01-130a84e1b049`
- **Canonical JSON Artifact:** [`C01-SDK-RUNNER-REPORT-20260828.json`](./C01-SDK-RUNNER-REPORT-20260828.json)
- **Checksum do Payload Canônico (SHA-256):** `sha256:6eeb596468336fc8d14cac3e97d59458c50451a3d8e286ef377669c613e9b23d`
- **Checksum do Arquivo JSON (SHA-256):** `sha256:4465ec3deedaf3e34bdb69cd1a0abcdac3079e8c93e5b2fd8048838af110a92d`

## Classificação OAuth

A rodada comprovou uma troca authorization-code + PKCE com grant sintético pré-provisionado; não executou login interativo real.

## Matriz C01

| Capacidade | Status |
| --- | --- |
| `protected_resource_discovery` | **PASS** |
| `authorization_server_discovery` | **PASS** |
| `oauth_pkce_s256` | **PASS** |
| `token_exchange` | **PASS** |
| `mcp_initialize` | **PASS** |
| `mcp_tools_list` | **PASS** |
| `memory_write_synthetic` | **PASS** |
| `memory_search_synthetic` | **PASS** |
| `memory_update_synthetic` | **PASS** |
| `memory_forget_synthetic` | **PASS** |
| `token_refresh_rotation` | **PASS** |
| `token_revocation` | **PASS** |
| `forged_authority_rejection` | **PASS** |
| `zero_leakage_redaction` | **PASS** |

## Negativos

- `unauthenticated_mcp_401`: **PASS**
- `authorization_code_replay_rejected`: **PASS**
- `old_refresh_rejected`: **PASS**
- `revoked_access_rejected_401`: **PASS**
- `forged_authority_explicit_rejection`: **PASS**
- `cross_tenant_explicit_rejection`: **PASS**
- `tombstone_non_resurrection`: **PASS**
