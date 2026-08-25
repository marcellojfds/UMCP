# R01 — documentação e playbooks pós-M1

**Status:** `DONE — local documentation integration`
**Branch:** `codex/roadmap-implementation`
**Base SHA:** `337efa5eba528e3635b1c36e5584732ea37763aa`
**Delivery SHA:** `b64f33c` (commit local de entrega)
**Final SHA:** `017c60e268a6922409a533f98e9414b0f9e35911` (SHA após registrar este handoff)

## Acceptance test congelado antes da implementação

R01 é aceito somente se, no mesmo candidato local e limpo:

1. o plano M03–M08, os oito playbooks MCP e o gap report GCP estiverem
   presentes nos paths canônicos e forem navegáveis a partir do guia;
2. somente a linha R01 do checklist mudar de `[ ]` para `[x]`;
3. os claims GCP forem classificados como proposta local / `PARTIAL /
   NOT-READY`, sem promover healthcheck, IaC ou handoff declaratório a
   `DONE`, `VERIFIED` ou `PRODUCTION-READY`;
4. os gates sintéticos M1 e web do R00 continuarem verdes, ou suas mudanças de
   estado forem explicitamente classificadas; e
5. não houver código, IaC, deploy, credencial, serviço externo, dado real,
   holdout, publicação, push, PR, tag ou release.

## Entrega e classificação

Integrados seletivamente dos SHAs-fonte:

- `4639f7f`: `docs/handoffs/roadmap/M03-M08-PRODUCT-EXECUTION-PLAN.md`;
- `de9ba6d`: `docs/execution/mcp-readiness/01-BASELINE-LOCAL-MCP.md` até
  `08-BETA-RELEASE-READINESS.md`;
- `106ec89`: `docs/handoffs/roadmap/M02-GCP-ADOPTION-GAP-REPORT.md`.

O contrato hosted `ef949f3` e todos os paths de implementação M2/GCP ficaram
fora do R01. A documentação importada é `integrated-current`; seus gates de
execução são `not-run` porque R01 não implementa essas capacidades. O gap
report é a fonte de claims e rebaixa os artefatos GCP para `PARTIAL /
NOT-READY`; não há claim de staging aceito, release ou produção.

## Comandos e resultados

| Gate | Comando | Freshness | Resultado |
| --- | --- | --- | --- |
| contexto | `pwd; git branch --show-current; git rev-parse HEAD; git status --short --branch` | current | PASS — base `337efa5...`, branch esperada, árvore inicial limpa |
| paths integrados | `test -f ...` para plano, 8 playbooks e gap report | current | PASS — todos presentes |
| links | `python`/checagem equivalente dos destinos relativos no guia | current | PASS — links apontam para os artefatos integrados |
| claims GCP | `rg -n 'PARTIAL|NOT-READY|DONE|VERIFIED|PRODUCTION-READY' docs/handoffs/roadmap/M02-GCP-ADOPTION-GAP-REPORT.md docs/roadmap_implementation.md` | current | PASS — claims não sustentados não são promovidos |
| R00 ASGI | `pytest -q tests/contract/test_m1_http_transport.py` | current | PASS — 3 passed |
| web | `cd apps/web && npm test && npm run check && npm run build` | current | PASS — gate R00 preservada |
| suíte documental | `git diff --check` | current | PASS |
| PostgreSQL/socket/browser | gates R00 correspondentes | current | environment-blocked/not-run, não tratados como pass |

## Skips e claims permitidos

Não foram executados Docker, sockets HTTP black-box, browser E2E, deploy,
Terraform, APIs GCP ou qualquer provider externo. Isso mantém os skips de R00
como `environment-blocked`/`not-run`. R01 permite afirmar integração local de
documentação e navegação; não permite afirmar M2 hosted, staging, beta, release,
produção ou readiness remoto.

## Rollback e próximos bloqueios

Rollback local: reverter o commit de entrega R01 ou remover os artefatos
documentais integrados após mudar para outra ref; nenhuma alteração remota foi
feita. Próximos bloqueios são R02/H01: integração das lanes locais válidas de
M2/M3 e decisões/controles hosted GCP. Os blockers P0 do gap report permanecem
abertos (identidade, acesso público, IAM/WIF, rede privada, segredos/KMS,
RLS/restore e observabilidade).
