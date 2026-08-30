---
title: 08 — Preparar beta fechado e release auditável
status: historical-superseded
order: 8
owner: Terra high + Luna high + auditor independente
depends_on: 07-TRUSTED-RECALL.md
unlocks: human release decision
---

# 08 — Preparar beta fechado e release auditável

## Resultado esperado

O UMCP chega a um release candidate local, reproduzível e auditável. Um beta
fechado com 5–20 usuários só abre após aprovação explícita; publicação, push,
tag, package, container, domínio e GA continuam autorizações separadas.

## Escopo beta

- onboarding e suporte;
- feature flags, quotas e kill switches;
- analytics opt-in agregada;
- console operacional sem leitura casual de conteúdo;
- incident, abuse e security reporting;
- restore/delete e rollback drills;
- capacity/cost baseline;
- export/delete account;
- privacy, retention e subprocessors;
- beta notes e feedback taxonomy.

## Escopo release Community

- quickstart limpo;
- wheel/sdist e migrations empacotadas;
- exemplos Python/TypeScript;
- docs de upgrade/forward-fix/restore;
- license, governance, DCO, CODEOWNERS e templates;
- CI obrigatório, secret/dependency/license scans;
- SBOM, provenance, checksums e signing quando suportado;
- vulnerability reporting;
- changelog e semantic versioning;
- auditoria independente S07-R2 equivalente.

## Tarefas executáveis

1. Congelar candidate SHA e inventário de paths.
2. Executar suite completa e gate freshness.
3. Rodar clean install/build em plataformas declaradas.
4. Gerar e validar SBOM/checksums/package contents.
5. Executar restore/delete/incident/rollback drills.
6. Medir SLO/capacity/cost em carga declarada.
7. Revisar privacy, security, support e claims.
8. Fechar P0/P1 ou registrar aceitação formal com owner/data.
9. Solicitar e executar auditoria independente.
10. Preparar plano de beta, sem convidar usuários ainda.
11. Pedir autorizações separadas para beta/holdout/publicação.
12. Só após aprovação, abrir a ação externa correspondente.

## Acceptance test

Uma pessoa nova consegue instalar Community, iniciar PostgreSQL, conectar um
cliente, escrever, buscar, atualizar e esquecer. Um usuário beta sintético
consegue completar onboarding, conectar dois clientes, revisar provenance,
exportar, revogar e apagar. Restore não ressuscita forget; operador observa
saúde sem ler conteúdo; rollback é executável.

## Comandos de aceitação

```bash
git diff --check
./scripts/gate-fast
./scripts/gate-postgres
python -m pytest -q
python -m build
python scripts/verify-package-contents --path dist
python scripts/generate-sbom --output /tmp/umcp-sbom.json
python scripts/check-clean-install --workdir /tmp/umcp-clean-install
python scripts/run-restore-delete-drill --synthetic
python scripts/release-preflight --candidate-sha <SHA>
```

## Gate de saída

- nenhum P0/P1 aberto sem aceitação formal;
- holdout GO no SHA candidato, se autorizado;
- auth/RLS/crypto/restore/delete auditados;
- SLO observado no beta, não prometido por wishful thinking;
- clean install e artifacts por SHA;
- CI/branch protection atuais e comprovados remotamente quando autorizados;
- auditor independente registra GO;
- mantenedor autoriza cada ação de publicação.

## Rollback

- fechar onboarding e novos signups;
- revogar credenciais afetadas;
- desabilitar auto-capture/conector problemático;
- rebaixar claims e matriz de compatibilidade;
- restaurar em isolamento e reaplicar tombstones;
- retirar artifact/publicação somente pela lane autorizada;
- criar novo candidate SHA, nunca sobrescrever evidência.

## Prompt de execução

```text
Execute docs/execution/mcp-readiness/08-BETA-RELEASE-READINESS.md depois de
validar os handoffs 01–07. Prepare um RC local reproduzível, execute drills,
clean install, supply-chain e auditoria independente. Não convide usuários,
execute holdout, publique, faça push/PR/tag/release ou aceite custo sem
autorização específica. Entregue decisão GO/NO-GO baseada no mesmo SHA e liste
claramente as ações humanas restantes.
```
