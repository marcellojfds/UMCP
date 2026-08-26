# H05 handoff — login e consent UX

## Estado

`DONE — UX local sintética / fail-closed`. A entrega cobre o fluxo de login,
callback, consentimento e conexões em um fixture contratual local. Não há IdP,
OAuth real, e-mail, credencial durável, cliente registrado, redirect externo,
provider, deploy, staging ou produção. CP-2 continua bloqueando a integração
real.

## Base, entrega e paths

- SHA base canônico: `84557eb55825d6140846d2383ac5ebb14b27831f`.
- SHA de implementação: `5b699d5ce9ec7f95bd1404e8a07fe6ff5730a373`.
- Paths de implementação:
  `apps/web/index.html`, `apps/web/src/app.js`,
  `apps/web/src/auth-fixture.js`, `apps/web/src/styles.css`,
  `apps/web/tests/auth-fixture.test.mjs`, `apps/web/README.md` e
  `src/omp/cloud/admin.py`.
- Paths de documentação/checklist: este handoff e somente a linha H05 em
  `docs/roadmap_implementation.md`.
- Dados: somente identificadores, escopos, timestamps e e-mails sintéticos;
  o fixture mantém sessão e estado apenas em memória do processo.

## Entrega

- Login local sintético com ramos `Continue with Google` e magic link,
  callback com `state`, expiração e uso único.
- Tela de consentimento com cliente, finalidade, política e scopes fornecidos
  pelo adapter; o browser envia apenas grant/deny e não pode expandir scopes,
  tenant ou owner.
- Deny não cria conexão; grant cria consent versionado e conexão ativa.
- `/connections` exibe estado, scopes, `last_used_at` server-owned e revoke;
  revoke torna a sessão correspondente inutilizável no fixture.
- Loading, retry, expired, denied, error e revoked têm estados explícitos; a
  UI usa controles nativos, foco/teclado, layout mobile e `prefers-reduced-motion`.
- Adapter real continua sendo injetável. Com Admin API same-origin existente,
  magic link permanece no callback/session HttpOnly server-side; Google não é
  habilitado sem decisão CP-2 e consentimento exige adapter H04 injetado.

## Evidência de testes

| Comando | Resultado |
| --- | --- |
| `npm test` em `apps/web` | PASS — 12 testes |
| `npm run check` em `apps/web` | PASS — sintaxe JS |
| `npm run build` em `apps/web` | PASS — build local |
| `pytest -q tests/unit/test_h04_identity_contracts.py tests/contract/test_admin_api.py` | PASS — 13 testes; 1 warning de depreciação do TestClient |
| `ruff check src/omp/cloud/admin.py tests/unit/test_h04_identity_contracts.py` | PASS |
| `git diff --check` | PASS |

O Browser local carregou a interface, mas a política do ambiente bloqueou o
reload necessário para garantir a versão atualizada. A verificação visual/E2E
foi classificada `environment-blocked`, não como PASS; não houve navegação para
provider externo. Os testes do fixture cobrem as transições contratuais de
callback, consentimento, deny, expiração, uso único e revoke.

## Claims e limites

Claim permitido: UX e adapter contratual sintéticos, locais e fail-closed,
compatíveis com as formas H04, sem credencial persistida no browser.

Claims proibidos: Google/OIDC operacional, OAuth hosted, provider escolhido,
registro de cliente, redirect allowlist operacional, entrega de e-mail,
staging, produção, segurança operacional ou browser E2E contra IdP.

## Rollback

Reverter localmente o commit `5b699d5` e o commit deste handoff remove a
implementação H05, sua evidência e a checkbox H05. H03 e H04 permanecem no SHA
base; nenhuma alteração externa existe para rollback.

## Próximo bloqueio

H06 continua independente. H07 depende de H05, H06 e dos checkpoints CP-1,
CP-2 e CP-3; qualquer integração real de IdP, cliente, redirect, e-mail,
provider, secrets ou deploy exige autorização explícita nesses checkpoints.
