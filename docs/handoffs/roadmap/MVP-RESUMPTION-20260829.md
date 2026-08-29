# UMCP MVP resumption handoff — 2026-08-29

**Decisão de retomada:** `H07 GO`; `C01/C02 implementação pronta, gate ainda
aberto`; `C03 não iniciado`.

Este é o ponto de entrada canônico para uma nova sessão com contexto limpo. O
objetivo imediato é colocar o MVP privado controlado em condição utilizável o
mais rápido possível, sem produção, usuários reais, publicação open source ou
expansão do escopo GCP.

## Leia primeiro

1. `docs/handoffs/roadmap/MVP-RESUMPTION-20260829.md`;
2. `docs/roadmap_implementation.md`;
3. `docs/handoffs/roadmap/H07-AUDIT-20260828.md`;
4. `docs/handoffs/roadmap/C01-SDK-RUNNER-REPORT-20260828.md`;
5. `docs/handoffs/roadmap/C02-CONTROLLED-AGENT-REPORT-20260828.md`;
6. `docs/handoffs/roadmap/CONTAINMENT-REPORT-20260828.md`.

`docs/handoffs/roadmap/H07-RESUMPTION-20260827.md` é histórico e foi
supersedido por este handoff.

## Repositório e limites

- worktree: `/private/tmp/umcp-pr1`;
- branch: `codex/fix-pr-1`;
- HEAD limpo recebido do AGY:
  `b462bccec5bdea2db40d6aaac30e3cdd449e503d`;
- preservar o checkout principal sujo;
- não usar manager ou subagentes salvo nova autorização explícita;
- não fazer push, PR, tag, release, produção ou convite a usuários;
- nunca registrar tokens, códigos OAuth, e-mails, connection strings ou
  valores de Secret Manager.

O único staging autorizado continua sendo:

| Recurso | Valor |
| --- | --- |
| projeto | `umcp-mcp-staging-20260825` |
| região | `us-central1` |
| serviço | `umcp-cloud-staging` |
| migration job | `umcp-migrate-staging` |

## Estado comprovado

### H07 / M2

H07 permanece fechado. A evidência canônica está em
`docs/handoffs/roadmap/H07-AUDIT-20260828.md`.

| Campo | Valor |
| --- | --- |
| server source SHA | `367cd365df43f9282f5155394cd39275169bf8f2` |
| server image digest | `sha256:764263db4907ffbbbd50e77ab7d12e8d88cde2b5990a9879a40ddbd0976e4f1d` |
| revisão ativa | `umcp-cloud-staging-00018-f78`, 100% do tráfego |
| migration execution | `umcp-migrate-staging-w9ld8` |
| migration head | `0011_oauth_authorization_codes` |
| decisão | `M02 STAGING READY`, nunca production-ready |

### Rodada C01/C02 mais recente

O AGY produziu uma imagem imutável de auditoria
`sha256:c39b3d02785b0a4f817da4074136b4d662c49085499e6cebbf8a69b96ccbedea`,
executou diretamente `python -m omp.sdk.audit_entrypoint` e registrou:

- C01: 14/14 capacidades `PASS`;
- C02: 15/15 passos `PASS`;
- contenção: `active_tokens=0`, `active_codes=0`,
  `active_test_tenants=0`;
- checksums canônicos e hashes físicos dos três JSONs conferem quando
  recalculados diretamente com a biblioteca padrão.

A implementação relevante está em:

- `src/omp/sdk/agent.py`;
- `src/omp/sdk/runner.py`;
- `src/omp/sdk/audit_entrypoint.py`;
- `src/omp/sdk/checksums.py`;
- `scripts/run_c01_c02_audit.py`;
- `scripts/verify_checksums.py`.

## Único bloqueio para fechar C01/C02

A execução não está ligada a um commit reproduzível:

- os reports dizem `audit_source_sha=72b9fad4...`;
- os arquivos efetivamente usados pela imagem só foram commitados depois em
  `b462bccec5bd...`;
- portanto a imagem foi construída a partir de uma árvore ainda não
  commitada, embora seu digest seja imutável.

Além disso, `python3 scripts/verify_checksums.py` falha num checkout sem as
dependências do pacote porque importar `omp.sdk.checksums` executa
`omp.sdk.__init__` e exige `anyio`. A verificação independente equivalente com
`hashlib` e `json` passou, mas o comando versionado deve funcionar em ambiente
limpo ou declarar suas dependências.

Por isso C01 e C02 ficam `[ ]` até a reexecução limpa. Não reabrir H07 e não
refazer a infraestrutura do servidor.

## Próxima sessão — caminho mínimo

1. Corrigir `scripts/verify_checksums.py` para funcionar somente com a
   biblioteca padrão, sem importar `omp.sdk`.
2. A partir da árvore limpa em `b462bccec5bdea2db40d6aaac30e3cdd449e503d`,
   construir uma nova imagem de auditoria e obter o digest imutável.
3. Executar o job com `audit_source_sha` exatamente igual a esse commit e
   `server_source_sha` separado, preservando a revisão `00018-f78`.
4. Confirmar C01 14/14, C02 15/15 e contenção 0/0/0 na mesma execução/ciclo,
   sem segredos nos logs.
5. Regerar os JSON/Markdown, rodar o verificador independente e os checks
   locais. Somente então marcar C01 e C02 `[x]` e criar commit limpo.
6. Depois disso, iniciar C03 sob CP-4. C03 é a primeira superfície externa
   real e o próximo passo para um MVP que outra pessoa consiga testar.

## Definição prática do MVP

- **MVP técnico controlado:** H07 + C01 + C02 com evidência limpa por SHA.
- **MVP testável por terceiros:** exige pelo menos C03, credencial/cliente
  externo autorizado em CP-4, onboarding mínimo, revoke/delete visíveis,
  quota/kill switch e canal de suporte. Ainda não está pronto para convite.
- **Private managed beta formal:** permanece no bloco B do roadmap e não deve
  ser confundido com uma demonstração técnica de C03.

## Prompt curto para retomar

```text
Continue diretamente no worktree /private/tmp/umcp-pr1, branch
codex/fix-pr-1, sem manager e sem subagentes. Leia primeiro
docs/handoffs/roadmap/MVP-RESUMPTION-20260829.md e
docs/roadmap_implementation.md. Preserve H07. Feche somente a lacuna de
proveniência C01/C02: corrija o verificador stdlib-only, construa a imagem de
auditoria a partir do HEAD limpo por digest imutável, execute 14/14 + 15/15 +
contenção 0/0/0 com audit_source_sha exato, regenere evidências e só então
marque C01/C02. Não avance C03, produção, usuários, push ou PR.
```

## Riscos que não podem ser apagados documentalmente

- staging pronto não significa produção ou beta aberto;
- o serviço ainda não oferece landing page/dashboard hospedados;
- C03 e CP-4 ainda estão abertos;
- os reports atuais são evidência operacional útil, mas não fecham o gate até
  a reexecução vinculada ao SHA limpo.
