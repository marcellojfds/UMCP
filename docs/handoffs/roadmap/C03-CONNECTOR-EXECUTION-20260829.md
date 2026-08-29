# Handoff C03 — Configuração dos Conectores e Demonstração Cross-Assistant

**Data:** 2026-08-29  
**Status:** READY / EXECUTABLE  
**Worktree:** `/Users/marcellojunqueirafranco/.codex/worktrees/d2fa/UMCP`  
**Branch:** `codex/w01r1-controlled-integration`  
**Base:** `965044a` (W01R1 C01/C02 Pass)

---

## 1. Entregas de C03

1. **Configuração para ChatGPT Custom MCP App (Web):**
   - Arquivo: `examples/connectors/chatgpt_mcp_config.json`
   - Endpoint: `https://umcp-cloud-staging-yqjlathj7q-uc.a.run.app/mcp`
   - Protocolo: Streamable HTTP com OAuth 2.0 (PKCE S256).

2. **Configuração para Gemini CLI (Local MCP Client):**
   - Arquivo: `examples/connectors/gemini_cli_config.json`
   - Formato padrão para `settings.json`.

3. **Demonstrador End-to-End Cross-Assistant:**
   - Script: `examples/e2e_cross_assistant_hosted.py`
   - Validação unitária: `tests/unit/test_cross_assistant_hosted.py` (PASS)
   - Fluxo comprovado:
     1. Persona A (ChatGPT) grava fato de preferência no vault com proveniência.
     2. Persona B (Gemini) recupera o fato exato via busca semântica.
     3. Persona B atualiza para versão 2.
     4. Persona A valida a versão atualizada.
     5. Esquecimento seguro (`memory.forget`) e confirmação de ciclo.

---

## 2. Instruções de Catch-up para Codex / GPT

Se a sessão for retomada pelo Codex / GPT:
- Os marcos **H07**, **C01** e **C02** foram completamente validados e fechados com checksums determinísticos.
- Os conectores de **C03** estão disponíveis em `examples/connectors/` e o demonstrador em `examples/e2e_cross_assistant_hosted.py`.
- O próximo passo para completar o MVP vertical é conectar a interface web (`apps/web`) para gerenciamento e revogação de conexões (marco H05 / A03).
