# Privacidade do Open Memory Protocol Alpha v0

## Escopo da garantia

O Alpha v0 é um software local/self-hosted. Ele não oferece E2EE, zero
knowledge, autenticação hosted ou isolamento de tenants não confiáveis. O
operador da instância e qualquer pessoa com acesso ao banco, processo, backup
ou arquivo exportado pode ler dados de memória.

No transporte local atual, `owner_id` é fornecido pelo cliente e tratado como
confiável. Ele separa dados logicamente, mas não substitui autenticação nem
autorização. Uma implantação exposta a usuários não confiáveis precisa de um
boundary de identidade que ainda não existe neste projeto.

## Inventário de dados

| Dado | Local | Sensibilidade | Estado atual |
|---|---|---|---|
| conteúdo e memória corrente | PostgreSQL | alta | plaintext para o operador |
| histórico de versões | PostgreSQL | alta | apagado pelo forget online |
| provenance/evidence | PostgreSQL | alta | plaintext para o operador |
| embeddings `hash/v1` | PostgreSQL/pgvector | alta | sensíveis; não são anônimos |
| relações, type, state, space e timestamps | PostgreSQL | média/alta | metadata pesquisável |
| owner e IDs | PostgreSQL/requests | média/alta | owner não deve entrar em logs |
| ledger de update/forget | PostgreSQL | média | metadata-only, sem conteúdo |
| exports `omp.export.v0` | arquivo escolhido pelo usuário | alta | vetores omitidos por default |
| configuração e URL do banco | ambiente/processo | alta | segredo não deve ser logado |
| logs | stderr/destino do operador | baixa por design | allowlist sem payload |
| eval artifacts | workspace/CI | baixa apenas se sintéticos | dados reais são proibidos por default |
| backups | responsabilidade do operador | alta | runbook lógico testável; retenção é do operador |

## Fluxo de dados atual

```text
cliente local
  -> MCP stdio (conteúdo, query, owner_id)
  -> adapter/gateway/application service
  -> embedding hash local
  -> PostgreSQL + pgvector

CLI administrativo
  <-> application service
  <-> arquivo omp.export.v0 escolhido pelo usuário
```

O profile `hash/v1` é executado localmente e não envia conteúdo a um provedor
externo. Adapters futuros de embedding/LLM deverão ser opt-in, documentar quais
dados saem da instância e nunca reutilizar dados para treinamento sem escolha
explícita do operador/usuário.

## Retenção e exclusão

| Superfície | Regra atual |
|---|---|
| memória, histórico, vetor e relações | persistem até `memory.forget` |
| forget online | remove memória, versões, vetor e relações na mesma transação |
| ledger de idempotência | permanece metadata-only para replay; não contém payload |
| export | persiste até o usuário apagar o arquivo; não é revogado pelo forget do banco |
| logs | retenção definida pelo ambiente do operador; o app não registra conteúdo por design |
| backups | runbook de backup/restore e reaplicação de forget existe; retenção e descarte são definidos/executados pelo operador |

O forget não apaga cópias já exportadas, logs externos indevidamente
configurados nem backups fora do controle do processo. O restore exige
reaplicar deleções antes de uso; como não existe uma fila externa de tombstones,
o operador precisa preservar e aplicar a lista de deleções. Não há garantia de
apagamento imediato de backups/exports.

## Controles implementados e evidência

- Schemas estritos e limites de entrada: testes de contrato MCP.
- Owner isolation no repository: suíte PostgreSQL real.
- Forget transacional e cascade: testes de integração e E2E.
- Export owner-scoped e sem embeddings por default: testes unitários,
  integração e E2E.
- Logging por allowlist sem conteúdo/query/owner bruto: observability tests,
  scan de canário/secrets/PII sintético em stderr e trace-capture de teste.
- Erros públicos sem SQL, stack trace ou payload: testes de contrato.
- Secrets encapsulados por `SecretStr` e omitidos do resumo de configuração.

Esses controles reduzem exposição acidental; eles não protegem contra um
operador malicioso, dump do banco, processo comprometido ou cliente que possa
forjar outro `owner_id`.

## Claim matrix

| Afirmação | Classificação | Base |
|---|---|---|
| persistência local em PostgreSQL | garantido no ambiente suportado | gate Postgres/E2E |
| separação lógica por owner | mitigado no modo local confiável | filtros e testes cross-owner |
| logs do aplicativo sem conteúdo por default | garantido para logger do OMP | allowlist e canary scan |
| forget remove os dados online do banco | garantido no escopo transacional testado | integration/E2E |
| embeddings não saem no export padrão | garantido | contrato `omp.export.v0` |
| operador não consegue ler memórias | não protegido | dados em plaintext |
| tenant não consegue forjar identidade | não protegido | auth hosted ausente |
| E2EE/zero knowledge | futuro, não disponível | Gate F |
| apagamento imediato de backups/exports | não protegido | cópias externas ao processo; deleções são reaplicadas no restore |
| privacidade de embeddings | não protegido | embeddings são dados sensíveis |

## Responsabilidades do operador

- restringir acesso ao host, banco, socket/processo e arquivos exportados;
- usar credenciais próprias e nunca versionar `.env` ou URLs com secrets;
- criptografar disco/backups quando necessário;
- definir retenção e descarte de logs/backups;
- não expor o servidor como serviço multiusuário sem autenticação/autorização;
- revisar qualquer provider externo antes de habilitá-lo.

## Antes de um release público

Ainda são obrigatórios: threat model revisado, teste de backup/restore/delete,
scan de secrets/PII em CI, canal privado de security reporting, política de
retenção operacional e revisão da claim matrix contra README/release notes.
