---
title: 05 — Comprovar conectores em clientes reais
status: ready-after-04
order: 5
owner: Luna high, Terra para correções de gateway
depends_on: 04-MULTITENANCY-SECURITY.md
unlocks: 06-PRODUCT-UX-AND-LANDING.md
---

# 05 — Comprovar conectores em clientes reais

## Resultado esperado

Pelo menos duas superfícies reais diferentes completam a jornada autenticada:
uma registra uma memória e outra recupera, atualiza e esquece. A matriz pública
fica datada e distingue `Supported`, `Experimental` e `Unverified`.

## Ordem de execução

1. agente Python controlado pelo projeto;
2. ChatGPT developer mode;
3. Claude API ou cliente oficialmente documentado;
4. Gemini CLI;
5. agente TypeScript;
6. outras superfícies somente depois do contrato verde.

Cada integração externa exige capability preflight e autorização própria para
credencial, endpoint e uso de serviço.

## Pacote obrigatório por conector

- versão/data e transporte;
- fluxo de auth e scopes;
- recipe de instalação limpa;
- write/capture e provenance;
- search/recall e abstention;
- update/expected version;
- forget e confirmação destrutiva;
- revoke e erro de scope;
- prompts positivos, indiretos, negativos e destrutivos;
- limitações e report checksummed;
- atualização da compatibility matrix.

## Tarefas executáveis

1. Congelar o conformance runner comum.
2. Criar fixtures sintéticas cross-client.
3. Fechar SDK Python fino.
4. Fechar SDK TypeScript fino.
5. Criar recipe de cada superfície.
6. Executar o fluxo em um cliente por vez.
7. Registrar erros e diferenças de confirmação/scopes.
8. Validar revoke e unauthorized.
9. Repetir em uma segunda superfície real.
10. Executar jornada A→B e B→A quando suportado.
11. Atualizar matriz e claims.
12. Fazer auditoria independente dos relatórios.

## Acceptance test

- cliente A registra `lesson` sintética com provenance;
- cliente B do mesmo tenant a recupera com `reason_retrieved`;
- B atualiza com versão esperada;
- forget exige confirmação quando a superfície suporta;
- revogar A bloqueia A;
- B permanece funcional no próprio scope;
- cliente não autorizado recebe erro seguro;
- matriz não usa “works everywhere”.

## Comandos de aceitação

```bash
python -m pytest -q tests/conformance tests/connectors
python scripts/demo-m03-connectors --synthetic --report-dir /tmp/umcp-connectors
python scripts/check-compatibility-matrix --strict
python scripts/verify-connector-reports --report-dir /tmp/umcp-connectors
```

## Gate de saída

- duas superfícies reais diferentes passam;
- cada `Supported` tem report ID, data e versão;
- auth/revoke/forget validados;
- tunnel privado não é apresentado como distribuição pública;
- superfície não testada permanece `Unverified`;
- snippets funcionam a partir de instalação limpa.

## Rollback

- rebaixar conector para `Experimental`/`Unverified`;
- revogar conexão/credencial específica;
- remover recipe incorreta da navegação pública;
- manter protocolo e vault intactos;
- não apagar evidência histórica do relatório anterior.

## Prompt de execução

```text
Execute docs/execution/mcp-readiness/05-REAL-CLIENT-CONNECTORS.md uma
superfície por vez. Revalide documentação oficial no início da execução.
Não use credenciais, APIs externas ou endpoints sem autorização. Só marque
Supported após write/search/update/forget/revoke reais e report checksummed.
Termine com duas superfícies comprovadas, matriz honesta, handoff e commit.
```
