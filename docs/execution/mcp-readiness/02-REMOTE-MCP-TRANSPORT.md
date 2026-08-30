---
title: 02 — Implementar o transporte MCP remoto
status: historical-superseded
order: 2
owner: Terra high
depends_on: 01-BASELINE-LOCAL-MCP.md
unlocks: 03-AUTH-CONSENT-REVOCATION.md
---

# 02 — Implementar o transporte MCP remoto

## Resultado esperado

O mesmo application service usado pelo `stdio` fica disponível por MCP
Streamable HTTP oficial em `/mcp`, sem duplicação de regra de negócio. Stdio e
HTTP passam a mesma suíte de conformance e falham fechado quando uma dependência
obrigatória está ausente.

Este marco prova transporte. Ele não prova identidade, tenant isolation ou
prontidão pública.

## Pré-requisitos

- documento 01 concluído e seu handoff lido;
- contrato MCP v0 congelado;
- capability preflight do SDK MCP oficial, ASGI, loopback e processo de teste;
- decisão explícita sobre versões de protocolo suportadas.

## Escopo

- `/mcp` reservado ao protocolo MCP;
- health e readiness separados e sem dados sensíveis;
- lifecycle correto de sessões, reconnect, cancellation e timeout;
- paridade `stdio`/HTTP;
- schema estrito, request ID, rate-limit seam e erros opacos;
- conformance automatizada e demo local HTTP.

Fora do escopo: deploy GCP, domínio, TLS público, IdP, OAuth real, secrets,
clientes externos e publicação.

## Tarefas executáveis

1. Auditar o adapter HTTP existente sem assumir que health 200 significa MCP.
2. Congelar a matriz `tool × transport × resultado/erro`.
3. Montar Streamable HTTP usando o SDK MCP oficial.
4. Garantir que `stdio` e HTTP chamem a mesma façade.
5. Rejeitar unknown fields e versões/protocolos não suportados.
6. Cobrir initialize, tools/list, tools/call, reconnect e cancellation.
7. Manter request IDs opacos e timeout sem retry storm.
8. Fazer readiness verificar somente dependências necessárias, sem payload.
9. Criar conformance runner reutilizável por conectores.
10. Criar `scripts/demo-mcp-http-local` com recursos descartáveis.
11. Executar paridade e regressão v0.
12. Produzir handoff com lista de adapters ainda locais.

## Acceptance test

- o cliente oficial inicializa por HTTP;
- lista exatamente as tools publicadas na versão contratada;
- chama write/search/update/forget com a mesma semântica do stdio;
- reconnect não perde consistência;
- cancel/timeout não duplica mutação;
- schema inválido retorna erro opaco e estável;
- falha de banco torna readiness vermelha sem selecionar fake;
- nenhum conteúdo aparece em logs ou resposta de erro.

## Comandos de aceitação

```bash
./scripts/gate-fast
./scripts/gate-postgres
PYTHONPATH=src pytest -q tests/contract tests/e2e
python -m pytest -q tests/conformance -k 'stdio or http or parity'
./scripts/demo-mcp-http-local
./scripts/scan-runtime-output
```

## Gate de saída

- paridade stdio/HTTP `current` no SHA;
- conformance oficial executada, não inferida;
- nenhuma segunda implementação de lifecycle/ranking;
- HTTP sem identidade permanece marcado como local/test only;
- paths de deploy/IaC intocados;
- handoff informa versões negociadas e limitações.

## Rollback

- desabilitar composição HTTP por configuração;
- manter stdio como caminho suportado;
- reverter o adapter sem alterar domínio/repository;
- preservar migrations e usar forward-fix se houver mudança compatível.

## Prompt de execução

```text
Execute docs/execution/mcp-readiness/02-REMOTE-MCP-TRANSPORT.md após confirmar
o gate do documento 01. Entregue MCP Streamable HTTP local e paridade com
stdio sobre o mesmo application service. Não faça deploy nem implemente auth
fake. Registre qualquer dependência hospedada como externa. Feche com demo,
conformance atual, handoff e commit local.
```
