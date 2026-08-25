---
title: 03 — Implementar identidade, consentimento e revogação
status: ready-after-02
order: 3
owner: Terra high, Luna high para UX
depends_on: 02-REMOTE-MCP-TRANSPORT.md
unlocks: 04-MULTITENANCY-SECURITY.md
---

# 03 — Implementar identidade, consentimento e revogação

## Resultado esperado

Uma conexão MCP recebe um principal verificado, scopes mínimos e consentimento
registrado. No hosted, `owner_id` enviado pelo cliente é rejeitado ou ignorado;
revogar uma conexão bloqueia suas chamadas sem afetar outra conexão válida do
mesmo usuário.

## Decisões humanas necessárias

- provider de identidade/e-mail;
- orçamento e região de dados;
- domínio/callbacks autorizados;
- política de sessão, retenção e termos.

Sem essas decisões, o executor conclui adapters locais e contratos, mas não
inventa provider nem envia e-mail real.

## Escopo

- OAuth 2.1/OIDC e PKCE para clientes públicos;
- authorization server/protected resource metadata;
- login Google e magic link/OTP como métodos de identidade;
- scopes `memory:read/write/delete/export` e `connections:manage`;
- consentimento por conexão;
- access token curto, refresh rotation e revogação;
- callback allowlist, anti-enumeration e abuse controls;
- sessão web server-side em cookie seguro;
- principal interno imutável e audit-safe.

## Tarefas executáveis

1. Congelar o contrato de `Principal` e a matriz tool→scope.
2. Remover `owner_id` dos schemas hosted sem quebrar o modo local versionado.
3. Implementar token verification, issuer/audience/resource binding e JWKS.
4. Implementar PKCE, state/nonce e callback allowlist.
5. Criar consent screen com scopes legíveis.
6. Implementar conexão, refresh rotation, revoke e logout.
7. Implementar magic link/OTP server-side com anti-enumeration.
8. Impedir token, e-mail e callback secret em URL persistida/log/analytics.
9. Cobrir expired, replayed, wrong audience, wrong scope e revoked.
10. Criar adapter local de IdP/e-mail para testes sintéticos.
11. Integrar UX somente ao contrato server-side.
12. Produzir threat-model delta e handoff.

## Acceptance test

- login sintético cria sessão server-side;
- authorization exige PKCE e consentimento;
- principal vem do token verificado;
- payload com owner forjado não altera tenant/owner;
- conexão A com read/write funciona;
- conexão B sem delete não consegue forget;
- revoke A bloqueia A imediatamente conforme política;
- B continua operando nos próprios scopes;
- callback externo/open redirect é rejeitado;
- token expirado/replayed retorna erro opaco;
- logs/analytics não contêm token ou e-mail.

## Comandos de aceitação

```bash
python -m pytest -q tests/auth tests/contract tests/security
python -m pytest -q tests/e2e -k 'oauth or consent or revoke or session'
./scripts/demo-auth-consent-local
./scripts/scan-runtime-output
npm --prefix apps/web run test -- --grep 'login|consent|revoke'
```

## Gate de saída

- auth e revoke E2E `current`;
- forged owner rejeitado;
- scopes mínimos aplicados em gateway e service boundary;
- nenhuma auth apenas client-side;
- nenhuma mensagem revela se o e-mail existe;
- provider real permanece `unverified` até staging autorizado.

## Rollback

- revogar todas as credenciais do ambiente afetado;
- desabilitar novos authorizations;
- manter modo local separado e explicitamente confiável;
- rotacionar secrets somente por procedimento autorizado;
- restaurar sessão/provider anterior sem aceitar token não verificado.

## Prompt de execução

```text
Execute docs/execution/mcp-readiness/03-AUTH-CONSENT-REVOCATION.md. Primeiro
feche contratos e adapters locais; só use provider externo após decisão e
autorização explícitas. A identidade hosted deve vir do token verificado,
nunca de owner_id do cliente. Não envie e-mail real, configure secrets, faça
deploy ou publicação sem autorização específica. Entregue demo, gates,
threat-model delta, handoff e commit local.
```
