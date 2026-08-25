---
title: 01 — Fechar o baseline local do MCP
status: ready-to-execute
order: 1
owner: Terra high
depends_on: Alpha local existente
unlocks: 02-REMOTE-MCP-TRANSPORT.md
---

# 01 — Fechar o baseline local do MCP

## Resultado esperado

Ao concluir este documento, o UMCP possui uma única jornada local reproduzível,
em PostgreSQL real, usando o servidor MCP oficial via `stdio`. Dois clientes
simulados compartilham um owner local confiável, executam
`write → search → update → forget`, sobrevivem a restart e produzem evidência
no mesmo SHA.

Este marco não habilita hosted, multi-tenancy, OAuth, suporte a clientes reais
ou release público.

## Contexto obrigatório

Leia antes de editar:

- `docs/contracts/internal-application-services.md`;
- `docs/contracts/internal-repository.md`;
- `docs/contracts/mcp/v0/README.md`;
- `docs/handoffs/core-mvp0.md`;
- `docs/handoffs/mcp-mvp0.md`;
- `docs/EXECUTION_RELIABILITY_PLAYBOOK.md`;
- [plano M03–M08](../../handoffs/roadmap/M03-M08-PRODUCT-EXECUTION-PLAN.md).

## Escopo

- consolidar a composição suportada `MCP stdio → application service → PostgreSQL`;
- provar as quatro tools v0;
- validar idempotência, versão, owner isolation e restart;
- fechar migrations zero→head e upgrade-from-existing;
- criar um comando único de demonstração;
- classificar gates como `current`, `historical`, `not-run` ou
  `blocked-by-environment`.

Fora do escopo: HTTP remoto, OAuth, RLS hosted, KMS, UI, conectores externos,
holdout, deploy, push, PR e release.

## Tarefas executáveis

1. Fazer preflight de worktree, branch, SHA, status e runtime.
2. Congelar o acceptance test antes de alterar código.
3. Verificar que o runtime default usa PostgreSQL e falha fechado se o banco
   estiver indisponível.
4. Garantir que memory/file sejam usados somente em teste ou demo explícita.
5. Executar migrations zero→head em PostgreSQL 16 + pgvector descartável.
6. Exercitar `memory.write`, `memory.search`, `memory.update` e
   `memory.forget` pelo cliente MCP oficial.
7. Validar replay idempotente e conflito para fingerprint divergente.
8. Validar isolamento cross-owner em todas as operações.
9. Reiniciar servidor/cliente e repetir search/update/forget.
10. Criar ou corrigir `scripts/demo-cross-client-memory` como entrypoint único.
11. Rodar lint, types, unit, contract, PostgreSQL e E2E no HEAD.
12. Registrar handoff e commit local do marco.

## Acceptance test

Com dados sintéticos:

- cliente A grava uma lição;
- cliente B do mesmo owner a encontra;
- busca negativa retorna vazio;
- update com versão correta cria uma versão;
- update com versão antiga retorna `version_conflict`;
- replay idêntico não cria nova versão;
- outro owner recebe zero resultados;
- forget remove memória, versões, relações e vetor;
- segundo forget retorna estado idempotente;
- após restart, o resultado continua correto.

## Comandos de aceitação

```bash
git diff --check
./scripts/gate-fast
./scripts/gate-postgres
PYTHONPATH=src pytest -q tests/contract tests/e2e
PYTHONPATH=src python examples/e2e_two_clients.py
./scripts/demo-cross-client-memory
```

Se o último script não existir, sua criação faz parte do marco. Nenhum comando
recebe `pass` sem ter sido executado no SHA entregue.

## Gate de saída

- PostgreSQL sem skips;
- quatro tools v0 conformes;
- journey única reproduzível;
- cross-owner leakage zero;
- nenhum fallback silencioso para demo;
- logs sem conteúdo/query/secret;
- worktree sem alteração residual do marco;
- handoff com SHA, comandos, outputs resumidos, skips e próximos riscos.

## Rollback

- reverter apenas o commit local do marco;
- preservar migrations aplicadas em ambientes não descartáveis e usar
  forward-fix;
- manter o caminho Alpha anterior documentado até a nova composição passar;
- nunca apagar banco, dump ou trabalho do usuário para recuperar um teste.

## Prompt de execução

```text
Execute integralmente docs/execution/mcp-readiness/01-BASELINE-LOCAL-MCP.md.
Trabalhe em worktree própria, mantenha um único milestone ativo e feche a
jornada local MCP stdio → PostgreSQL com todas as gates atuais. Use apenas
dados sintéticos. Não implemente HTTP remoto, auth hosted ou UI. Não faça
holdout, deploy, push, PR, tag ou release. Termine somente com demo única,
handoff, commit local e status sem alterações residuais desta lane.
```
