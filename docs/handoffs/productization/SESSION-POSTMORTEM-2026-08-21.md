# Pós-mortem da sessão de integração local — 2026-08-21

## Conclusão direta

Esta sessão produziu código e testes, mas não foi conduzida de uma forma que
desse ao solicitante uma demonstração simples, contínua e inequívoca de
progresso. Essa crítica é procedente. O resultado atual é um candidato de
integração local, **não** uma entrega de produção e **não** uma evidência de
que todas as fases do objetivo foram concluídas.

O trabalho interrompido está em `product/integration`, commit `19fc215`, na
worktree `/private/tmp/umcp-product-integration`. A worktree está limpa.

## Evidência verificável do que mudou

Comparado ao baseline `2c94d5562368c14224c073a907d35c85063f7c0e`:

| Medida | Evidência |
| --- | --- |
| Commits locais | 60 (`git rev-list --count 2c94d556..19fc215`) |
| Alterações | 56 arquivos, 4.623 inserções e 62 remoções (`git diff --stat 2c94d556..19fc215`) |
| Janela de commits | 13:24–15:52 BRT em 2026-08-21 |
| Última validação | `./scripts/gate-fast`: lint, mypy e 72 testes Python passaram; 1 warning de depreciação de dependência de teste |

Os commits preservam os dois históricos recebidos: `ef8ebee` integra Terra e
`b57bff5` integra Luna. Não houve push, PR, deploy, e-mail real, dados reais
ou uso de chave comprometida.

## Implementação efetivamente presente

### Plano de dados e segurança Cloud

- Gateway MCP HTTP autenticado, fail-closed, com `/mcp`, `/healthz` e
  `/readyz`; contratos de token, escopo, expiração, revogação, limites e
  rejeição de `owner_id` forjado.
- Migrations `0005_cloud_multitenancy_rls`,
  `0006_cloud_envelope_storage` e `0007_tenant_fks`: tenants, RLS
  default-deny/FORCE RLS, tenant context e FKs compostas de memória para
  versões, embeddings e relações.
- Persistência PostgreSQL de conteúdo/provenance como envelopes cifrados,
  versionamento/rewrap de chave, tombstones e auditoria sem plaintext.
- Testes adversariais de RLS/tenant/owner, backup+tombstone, rotação e
  vazamento de canário em dump.

### Controle administrativo local e web

- API Admin local com magic link capturado em mailbox de desenvolvimento,
  sessão, CSRF, limites, logout, memória paginada/detalhe/update/forget,
  conexões, revogação, credenciais de agente, exportação solicitada e exclusão
  de conta.
- A exclusão local remove memórias do dono, grava tombstones sem conteúdo e
  revoga sessão, conexão e PAT local.
- Web Luna com adaptador Admin HTTP no mesmo origin para login, sessão,
  memórias, conexões, agentes e controles de conta; build/check/test locais.
- SDK TypeScript mínimo e runner de conformance contra `/mcp` autenticado.

### Worker — último incremento

O commit `19fc215` acrescenta snapshot/restauração de metadados assinados de
jobs retryáveis no worker local. Ele recusa snapshot adulterado, não restaura
jobs terminais e mantém payload como referência, não conteúdo. O teste cobre
falha, reinício, retry bem-sucedido e assinatura alterada.

## Validações realizadas

| Verificação | Resultado registrado |
| --- | --- |
| `./scripts/gate-fast` no commit `0d4fdba` | passou: lint, mypy e 73 testes Python |
| Teste focado de segurança Cloud | 10 passaram antes da porta completa |
| PostgreSQL descartável (`scripts/gate-postgres`) | 18 testes passaram no HEAD `1bd460e`; migrations zero→head concluídas em PostgreSQL 16.15 com pgvector 0.8.6 |
| SDK TypeScript | 2 testes passaram em execução anterior |
| Web | 3 testes, check e build passaram em execução anterior |
| Conformance MCP local autenticado | ciclo write/search/update/forget passou em execução anterior |
| Audit de dependências / segurança de CI | passaram em execução anterior |

As duas primeiras linhas são validações atuais do HEAD. As demais continuam
como evidência histórica e devem ser repetidas antes de qualquer conclusão de
release.

## Lacunas conhecidas — não ocultar

- Mailbox, sessões, conexões, credenciais, recibos de operação e fila do
  worker são adapters locais em memória. O snapshot recém-adicionado não é
  armazenamento durável de produção.
- Exportação retorna aceite/estado local; não entrega objeto criptografado para
  download.
- IdP/OIDC/JWKS real, KMS/HSM, e-mail, fila/worker durável, backups/restore,
  TLS/storage e deploy requerem infraestrutura e autorização externas.
- Não há evidência de browser E2E visual em desktop, 390px, teclado ou reduced
  motion. A inspeção do landing foi feita, mas três alternativas seguras para
  E2E falharam por limitação do ambiente: processos loopback são encerrados
  após o comando de teste, inclusive em segundo plano; navegação a arquivo
  local é bloqueada pela política do navegador. Portanto isso não deve ser
  contado como teste realizado.
- Não há afirmação de E2EE, zero knowledge, compatibilidade universal de
  clientes ou readiness de produção.

## Por que pareceu que não houve progresso

Há duas respostas, ambas importantes:

1. **O escopo era grande e interdependente.** O objetivo pede sete frentes:
   integração de duas branches, protocolo MCP remoto, auth, RLS/PostgreSQL,
   criptografia, Admin API, web, workers e gates. A implementação foi feita
   em muitos incrementos pequenos porque cada camada desbloqueava a seguinte.
   Isso gerou 60 commits em cerca de 148 minutos, mas reduziu a percepção de
   avanço por entrega.
2. **A execução foi mal empacotada para acompanhamento.** Em vez de travar
   marcos verificáveis (por exemplo: “gateway + auth demonstrável”, “RLS
   demonstrável”, “web demonstrável”) e só então seguir, foram alternados
   patches, correções, testes e documentos. Isso consumiu tempo e tokens sem
   apresentar um artefato final navegável ao usuário. A responsabilidade por
   essa falta de foco é da condução da sessão.

Também ocorreu um erro operacional concreto no final: o diretório inicial era
`/Users/marcellojunqueirafranco/Documents/UMCP`, branch
`terra-alpha-recovery`, com mudanças não relacionadas do usuário. A operação
foi interrompida antes de editar esses arquivos e redirecionada para a
worktree correta. Esse desvio foi detectado e não causou alteração na cópia do
usuário, mas é mais um sinal de que a sessão não estava mantendo o contexto de
execução de modo suficientemente claro.

## Linha do tempo completa de commits da integração

O histórico completo é a fonte de verdade. Para reprodução:

```sh
git -C /private/tmp/umcp-product-integration log --format='%h %ad %s' --date=iso-strict 2c94d556..19fc215
```

Marcos, em ordem cronológica:

- `ef8ebee` merge Terra; `b57bff5` merge Luna.
- `bf1656f` gateway MCP; `e43611b` Admin passwordless; `6b80e90` schema/RLS;
  `fffea01` memória cifrada; `d51cea6` runtime local cifrado; `9d4f348` worker/DLQ.
- `1e872ca`, `a4887fc`, `a913b5b`, `906f232`, `f8cbbcc`, `6c6159d`,
  `04925d2`, `cf74e1c`: integração gradativa da web/Admin.
- `a7e5e9f`, `e1fa53e`, `e1cf87f`, `50828ff`, `ba0cfe8`, `8c475ca`:
  envelopes e rotação/rewrap PostgreSQL.
- `e38d811`, `3625e9c`, `3f4da2b`, `a84d07a`, `e753829`, `4f01fd7`:
  provas de RLS, tenant-bound writes e isolamento cross-tenant.
- `e35efed`, `e9f0330`, `1eff255`, `9b25a63`, `6e99570`:
  tombstones, auditoria e exclusão de conta.
- `8d31a19`, `b6791c0`: conformance MCP local; `19fc215`: recuperação de
  retry de worker após reinício.

Para o detalhamento arquivo-a-arquivo, use:

```sh
git -C /private/tmp/umcp-product-integration diff --stat 2c94d556..19fc215
git -C /private/tmp/umcp-product-integration log --oneline 2c94d556..19fc215
```

## Estado seguro para retomada

Nenhuma nova implementação deve ser iniciada sem escolher um único marco
demonstrável. O ponto mais honesto para retomar é repetir as gates não atuais
(PostgreSQL, SDK, web, conformance), produzir uma demonstração local única e
só então decidir se há trabalho adicional. Não tratar este documento como
aprovação de release.
