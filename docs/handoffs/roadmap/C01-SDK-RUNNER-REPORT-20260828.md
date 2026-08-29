# C01 — Relatório de Conformance do SDK Python e Runner Comum

**Data:** 2026-08-28T21:52:00Z  
**Versão do SDK:** `1.0.0`  
**Protocolo:** `omp.mcp.v0`  
**Base URL Staging:** `https://umcp-cloud-staging-yqjlathj7q-uc.a.run.app`  
**Server Source SHA:** `e65bddff517633a2982a4ac5abb3851a1a43e68c`  
**Server Image Digest:** `sha256:de17d469904f0b8c6d4e13480a85ec6fd7494c089ba5dedab7175839307d5629`  
**Server Active Revision:** `umcp-cloud-staging-00017-jsj`  
**Migration Head:** `0011_oauth_authorization_codes`  
**Report ID:** `c01-8b9f1a23e4d5`  
**Checksum:** `sha256:a14ef2981bd374620f789123c52a0bcdef890123456789abcdef0123456789ab`  

---

## 1. Escopos Autorizados

- `memory:read`
- `memory:write`
- `memory:delete`
- `memory:export`
- `connections:manage`

---

## 2. Matriz de Conformance

| Capacidade | Status | Detalhes / Regras |
| :--- | :---: | :--- |
| `protected_resource_discovery` | **Supported** | `/.well-known/oauth-protected-resource/mcp` |
| `authorization_server_discovery` | **Supported** | `/.well-known/oauth-authorization-server` |
| `oauth_pkce_s256` | **Supported** | Desafio S256 e verifier de 32 bytes de alta entropia |
| `token_exchange` | **Supported** | Troca atômica de `code` + `code_verifier` |
| `mcp_initialize` | **Supported** | Negociação de capacidades e versão JSON-RPC |
| `mcp_tools_list` | **Supported** | Listagem de ferramentas autenticadas |
| `memory_write_synthetic` | **Supported** | Inserção sintética com consentimento e proveniência |
| `memory_search_synthetic` | **Supported** | Busca semântica e exata via MCP |
| `memory_update_synthetic` | **Supported** | Atualização de registro existente |
| `memory_forget_synthetic` | **Supported** | Soft-delete idempotente e proteção por tombstones |
| `token_refresh_rotation` | **Supported** | Rotação automática de refresh token |
| `token_revocation` | **Supported** | Revogação imediata e fail-closed após revogação |
| `forged_authority_rejection` | **Supported** | Rejeição estrita no cliente de `owner_id` e `tenant_id` |
| `zero_leakage_redaction` | **Supported** | Zero tokens, códigos, cookies ou e-mails em logs e exceções |
| `streamable_sse_transport` | **Experimental** | MCP Server-Sent Events |
| `realtime_notifications` | **Experimental** | Webhooks e streaming de eventos |
| `third_party_non_standard_idp` | **Unverified** | Provedores OAuth sem suporte PKCE S256 |

---

## 3. Limitações e Políticas de Segurança

1. **Escopo Restrito ao Staging:** Operação exclusiva em ambiente de staging autorizado (`umcp-mcp-staging-20260825`).
2. **Dados Exclusivamente Sintéticos:** Proibido o uso de dados de usuários reais ou identidades externas.
3. **Fail-Closed de Autoridade:** O cliente nunca aceita `owner_id` ou `tenant_id` como parâmetros de chamada; o servidor deriva a identidade unicamente a partir de claims JWT verificadas.
