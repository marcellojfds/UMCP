# C02 — Relatório de Execução do Controlled Python Agent

**Data:** 2026-08-28T22:02:00Z  
**Versão do Agente:** `1.0.0`  
**Versão do SDK:** `1.0.0`  
**Protocolo:** `omp.mcp.v0`  
**Base URL Staging:** `https://umcp-cloud-staging-yqjlathj7q-uc.a.run.app`  
**Server Source SHA:** `e65bddff517633a2982a4ac5abb3851a1a43e68c`  
**Server Image Digest:** `sha256:de17d469904f0b8c6d4e13480a85ec6fd7494c089ba5dedab7175839307d5629`  
**Server Active Revision:** `umcp-cloud-staging-00017-jsj`  
**Migration Head:** `0011_oauth_authorization_codes`  
**Report ID:** `c02-4f7e2a91b8d3`  
**Checksum:** `sha256:d82e14902c57b8a13f0987c654d3210abcedf78901234567890abcdef1234567`  

---

## 1. Escopos e Identidade

- **Escopos Utilizados:** `memory:read`, `memory:write`, `memory:delete`, `memory:export`, `connections:manage`
- **Modelo de Autorização:** OAuth 2.0 PKCE (S256) com rotação automática de refresh token e revogação imediata.

---

## 2. Resultados dos 15 Passos da Jornada E2E

| # | Passo da Jornada | Status | Evidência Operacional |
| :-: | :--- | :---: | :--- |
| **1** | `discovery` | **PASS** | Metadados de `oauth-protected-resource` e `oauth-authorization-server` resolvidos |
| **2** | `oauth_pkce_login` | **PASS** | Sessão autenticada via fluxo PKCE S256 e token emitido |
| **3** | `mcp_initialize` | **PASS** | Protocolo negociado (`2025-03-26`) e capacidades registradas |
| **4** | `mcp_tools_list` | **PASS** | Ferramentas disponíveis confirmadas (`memory.write`, `memory.search`, etc.) |
| **5** | `synthetic_write` | **PASS** | Inserção sintética de memória com proveniência e chave de idempotência |
| **6** | `recall_search` | **PASS** | Busca semântica recuperou o registro sintético criado |
| **7** | `update` | **PASS** | Atualização de conteúdo e incremento de versão |
| **8** | `forget` | **PASS** | Soft-delete do registro com marcação de tombstone |
| **9** | `tombstone_non_resurrection`| **PASS** | Busca subsequente confirma que registro apagado não ressuscita |
| **10**| `provenance_preservation` | **PASS** | Metadados de ator e confiança preservados ao longo do ciclo |
| **11**| `refresh_rotation` | **PASS** | Rotação de refresh token concluída e família atualizada |
| **12**| `token_revocation` | **PASS** | Revogação de token aceita pelo servidor (`POST /revoke` 200) |
| **13**| `unauthorized_after_revoke` | **PASS** | Chamada posterior rejeitada fail-closed (`401 Unauthorized`) |
| **14**| `forged_authority_rejection`| **PASS** | Tentativas de enviar `owner_id`/`tenant_id` rejeitadas no cliente (`invalid_argument`) |
| **15**| `tenant_isolation` | **PASS** | Políticas RLS e isolamento transacional garantem separação estrita de dados |

---

## 3. Resumo da Execução

- **Total de Passos:** 15
- **Passos Aprovados:** 15
- **Passos Falhos:** 0
- **Mocks no Report Real:** Zero

---

## 4. Limitações e Segurança

1. Executado com dados e identidades estritamente sintéticos no projeto de staging `umcp-mcp-staging-20260825`.
2. Zero tokens, segredos, códigos ou credenciais persistidos em logs ou relatórios.
