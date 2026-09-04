# Claude Custom Connector → Directory (caminho mínimo)

Checklist técnico para chegar ao 1-click no Connectors Directory **sem**
inventar GO de hosted/release. Status com evidência no repo ou na doc Anthropic.

Referências: [ADR 0017](../adr/0017-claude-client-memory-discipline.md),
[ADR 0010](../adr/0010-mcp-streamable-http-and-admin-api.md),
[ADR 0011](../adr/0011-cloud-identity-authorization-and-consent.md),
[Submitting to the Connectors Directory](https://claude.com/docs/connectors/building/submission).

## Escada

| Etapa | UX para o usuário | Pré-requisito |
| --- | --- | --- |
| Project Instructions | Cola texto no Project | Pronto hoje — ver `claude-project-instructions.md` |
| Custom Connector | Cola URL `https://…/mcp` e Connect | Remote MCP HTTPS + auth |
| Connectors Directory | Achou na lista e Connect | Custom funcionando + review Anthropic |

## Status por item

| Item | Status | Evidência |
| --- | --- | --- |
| MCP stdio local (Alpha) | **ready** (Desktop/local) | `docs/mcp.md`, `docs/support-matrix.md` |
| Tools v0 write/search/update/forget | **ready** (contrato) | `docs/contracts/mcp/v0/`, `docs/protocol.md` |
| Endpoint público Streamable HTTP `/mcp` | **NO-GO** (runtime Alpha) | Alpha = stdio only; ADR 0010 é **design** Cloud |
| `/_hosted_boundary` | **não é** MCP público | `src/omp/adapters/mcp/hosted.py` — seam de teste |
| OAuth / identidade hosted (M2) | **NO-GO** (sem claim produção) | ADR 0011 design; roadmap “future, not promised by Alpha” |
| Fixtures `claude-sim` | **não é** connector Claude | `examples/connectors/recipe.md` |
| Tool annotations `title` + `readOnlyHint` / `destructiveHint` | **gap a fechar** antes do Directory | Exigência Anthropic; ADR 0010 já prevê anotações no Cloud |
| Privacy policy + docs públicas + ícone + suporte | **parcial** | Docs Alpha existem; listing assets ainda não empacotados para Directory |
| Conta de teste populada para review | **NO-GO** até staging auth | Requisito do portal Anthropic |
| Org Claude Team/Enterprise + portal Directory | **fora do repo** | Submissão em Organization settings → Directory |
| Retrieval semântico Gate B (S08) | **NO-GO** | `docs/known-issues.md` (E5 precision@5≈0.756) |
| Release / tag / PyPI `0.1.0a1` | **NO-GO** | `CHANGELOG.md`, `README.md` |
| H07 / staging como GO | **não autorizado neste doc** | Sem evidência de GO neste checklist; não promover |

## Menor caminho técnico (quando autorizado a implementar)

1. Expor MCP Streamable HTTP em URL HTTPS pública estável (`/mcp`), conforme ADR 0010 — **não** reutilizar `/_hosted_boundary` como se fosse transport MCP.
2. Autenticar com OAuth 2.0 (consent por usuário); rejeitar `owner_id` confiado do cliente no boundary hosted (ADR 0011 / `docs/protocol.md`).
3. Registrar as quatro tools com `title` e hints: `memory.search` → read-only; `memory.write` / `memory.update` / `memory.forget` → destructive/write conforme o caso.
4. Testar como **Custom Connector** no Claude.ai: Customize → Connectors → Add custom connector → URL → Connect.
5. Exercitar write → search → update → forget com a disciplina assisted do ADR 0017.
6. Só então: org Team/Enterprise → Organization settings → Directory → submeter (docs, privacy, ícone, test account).

## O que está pronto para o maintainer hoje

- Colar Project Instructions (`claude-project-instructions.md`) no Project Claude.ai.
- Manter honestidade de gates: disciplina de cliente ≠ hosted GO ≠ marketplace.
