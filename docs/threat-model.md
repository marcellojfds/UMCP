# Threat model — Open Memory Protocol Alpha v0

**Versão:** 0.1
**Escopo:** execução local/self-hosted com MCP stdio e PostgreSQL 16 + pgvector
**Fora de escopo:** serviço hosted, auth multi-tenant, E2EE e providers externos

## Assets, atores e boundaries

Assets principais: conteúdo, histórico, provenance, embeddings, relações,
owners, exports, credenciais, logs, eval artifacts e backups.

Atores considerados: usuário local legítimo, operador da instância, processo
cliente comprometido, atacante com acesso ao host/banco/backup e dependência
maliciosa ou vulnerável. Um tenant remoto não confiável não é suportado.

```text
[cliente local confiável]
          |
          | MCP stdio: payload sensível
          v
[processo OMP] -- logs allowlist --> [stderr/coletor do operador]
     |     \
     |      \-- export sensível --> [arquivo do usuário]
     |
     +-- conexão autenticada --> [PostgreSQL/pgvector]
```

Trust boundaries: processo cliente/processo OMP, OMP/PostgreSQL, OMP/sistema
de logs e OMP/arquivo exportado. No Alpha, todos vivem sob controle do mesmo
operador; isso é uma premissa, não uma garantia criptográfica.

## Ameaças prioritárias

| ID | Ameaça | Impacto | Controle atual | Risco residual/ação |
|---|---|---|---|---|
| T01 | cliente forja `owner_id` | crítico em hosted | somente premissa local | bloquear hosted até identity boundary |
| T02 | operador/dump lê conteúdo | alto | acesso operacional | aceito e documentado; E2EE é futuro |
| T03 | embedding permite inferência | alto | não exportado por default | classificar como sensível e restringir acesso |
| T04 | cross-owner por filtro ausente | alto | constraints/filtros/testes reais | manter regression obrigatória em CI |
| T05 | log/error vaza payload ou secret | alto | allowlist e erros genéricos | canary/secret scan em toda PR e RC |
| T06 | export é copiado/exposto | alto | owner scope; vetor opt-in | warning, permissões e responsabilidade do usuário |
| T07 | forget deixa cópia em backup/export | alto | cascade online; runbook de backup/restore com reaplicação de deleção | operador conserva lista de deleções e descarta backups/exports |
| T08 | migration/falha parcial corrompe dados | alto | transações, Alembic, rollback tests | backup/restore e runbook de incidente |
| T09 | idempotency ledger guarda conteúdo | médio | fingerprints e metadata-only | schema/scan regression |
| T10 | dependency/supply-chain comprometida | alto | ranges de versão apenas | lock/constraints, audit e provenance de build |
| T11 | DoS por payload/query/concorrência | médio | limites e timeout | load test e budgets; sem claim de escala |
| T12 | artifact de CI contém dados | médio | fixtures sintéticas | scan e retenção mínima de artifacts |

## STRIDE por boundary

- **Spoofing:** `owner_id` é spoofable fora da premissa local. Não há mitigação
  para hosted no Alpha.
- **Tampering:** validação estrita, optimistic concurrency, fingerprints,
  migrations e transações detectam/reduzem alterações inconsistentes.
- **Repudiation:** request IDs e status ajudam diagnóstico, mas o Alpha não
  fornece audit log de identidade; não alegar non-repudiation.
- **Information disclosure:** principal risco. Conteúdo e embeddings são
  plaintext para o operador; logs são minimizados e exports são sensíveis.
- **Denial of service:** limites e timeouts existem, mas rate limiting e
  budgets/load gates ainda precisam ser fechados.
- **Elevation of privilege:** não existe papel/ACL hosted; qualquer exposição
  multiusuária sem novo boundary é insegura e fora de suporte.

## Requisitos de segurança do Alpha

1. Backend release não pode cair silenciosamente para demo/file.
2. PostgreSQL real e E2E rodam sem skip no gate obrigatório.
3. Toda operação de dados aplica owner scope no repository.
4. Conteúdo, query, provenance, vetor, raw owner e secrets não entram em logs,
   métricas, traces ou error messages.
5. Export exige owner explícito e omite vetores por default.
6. Forget remove memória, versões, vetor e relações atomicamente.
7. Configuração secreta não aparece em status/readiness.
8. CI usa somente dados sintéticos e faz secret/canary scan.
9. Dependências e artifacts de release são reproduzíveis e auditados.
10. README e release notes repetem as limitações de operador, auth, backups e
    embeddings.

## Plano de verificação restante

- tornar cross-owner, cascade, import rollback e canary scans obrigatórios na
  GitHub Actions com PostgreSQL/pgvector;
- testar readiness durante outage e encerramento do processo;
- executar backup, forget, restore e reaplicação de deletion policy em ambiente
  descartável; exigir cliente `pg_dump`/`pg_restore` compatível com o servidor;
- executar scanner de secrets sobre repositório, wheel/sdist, logs e artifacts;
- revisar permissões e warnings de arquivos exportados;
- fazer revisão independente deste documento antes do RC.

## Critérios de no-go

O release é bloqueado se qualquer teste cross-owner/cascade falhar, se conteúdo
ou secret aparecer em artifacts, se o quickstart sugerir exposição hosted, se
backup/restore não tiver política explícita ou se documentação insinuar E2EE,
zero knowledge ou privacidade de embeddings.
