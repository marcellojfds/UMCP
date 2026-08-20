# W11 — Observabilidade e operações

## Objetivo

Tornar OMP executável e diagnosticável em ambiente local/self-hosted, com telemetria segura, migrations controladas, health/readiness, worker operations e runbooks. O foco do MVP é confiabilidade básica e depuração sem registrar memória sensível.

## Contexto mínimo

O MVP usa um monólito modular e PostgreSQL/pgvector. O servidor pode ter entrypoints MCP e HTTP/ASGI; consolidação futura roda em infraestrutura externa. Hosting gerenciado e SLOs comerciais ficam posteriores ao aprendizado do alpha.

Leia W00, W01, W03, W04, W07, W08, W09 e W10.

## Escopo

### Dentro

- ambiente local reproduzível e configuração de serviços;
- liveness/readiness e dependency checks;
- structured logging, metrics e tracing hooks;
- redaction e cardinality controls;
- startup/shutdown, migration deployment e rollback runbooks;
- timeouts, retries, backpressure e graceful degradation;
- backup/restore/delete-retention procedure;
- execução/scheduling externo de workers;
- release health smoke tests e incident runbooks básicos.

### Fora

- lógica de domínio, writer, retrieval ou consolidation;
- schema de banco e migrations em si, owned por W03;
- plataforma cloud/managed hosting de produção;
- multi-region, autoscaling complexo, billing e SRE 24x7;
- coleta de conteúdo para analytics;
- privacy claims, owned por W07/W12.

## Sinais mínimos

### Logs estruturados permitidos

- request/job ID, tool/use-case, status, duration bucket;
- owner hash efêmero ou pseudônimo apenas se W07 aprovar;
- protocol/profile version;
- error code e dependency class;
- contagens e scores agregados sem query/content.

### Métricas mínimas

- requests por tool/status;
- latência p50/p95/p99 por operação;
- zero-result/abstention rate;
- candidate/result counts em buckets;
- embedding/LLM calls, timeout, retry, fallback e custo estimado;
- DB pool/latency/errors;
- worker runs/proposals/failures/checkpoint age;
- migration version e readiness.

Nunca usar conteúdo, query, provenance, embedding, raw owner ID ou high-cardinality memory ID como label.

## Decisões já tomadas

- Logs e telemetry sem conteúdo por default.
- Correlation ID atravessa adapter -> application -> dependency.
- Health endpoints não expõem configuração, credenciais, owner data ou stack traces.
- Readiness falha se dependência indispensável ao modo habilitado estiver indisponível.
- Retry só ocorre em operação segura/idempotente e com limite/backoff.
- Migrations não rodam implicitamente em toda instância concorrente sem coordenação.
- Local environment usa configuração reproduzível e dados sintéticos.
- Scheduled consolidation é externo ao MCP.

## Decisões abertas

- Docker Compose versus ferramenta equivalente para ambiente local;
- stack de OpenTelemetry/logs/metrics e exporters opcionais;
- budgets iniciais de latência/custo por tool;
- estratégia de migrations no deploy futuro;
- retenção de logs/backups;
- mecanismo de scheduled jobs no alpha;
- deployment reference opcional depois do release local.

## Dependências

- W01: app factory/config/entrypoints.
- W03: database health, migrations e restore.
- W04: transports/request IDs/errors.
- W07: data classification/redaction/retention.
- W08: budgets e metric definitions.
- W10: worker contract.

W09 usa status/smoke; W12 usa runbooks e setup.

## Entregáveis

- ambiente local one-command ou sequência curta documentada;
- health/readiness endpoints/checks;
- logging/metrics/tracing configuration segura;
- instrumentation dos application boundaries e dependencies;
- migration/rollback, backup/restore e incident runbooks;
- worker/scheduler reference para consolidation;
- smoke/load scripts com dados sintéticos;
- dashboard/queries de referência, se a stack permitir sem peso excessivo.

## Etapas

1. Receber data classification W07 e budgets provisórios W08.
2. Preparar ambiente local e health/readiness.
3. Definir event/metric names de baixa cardinalidade.
4. Instrumentar boundaries, database e providers com redaction.
5. Configurar timeouts/retries/fallbacks conforme semântica de cada frente.
6. Exercitar migration, restart, dependency outage e backup/restore.
7. Integrar worker externo quando W10 estiver disponível.

## Critérios de aceite verificáveis

- Novo executor sobe servidor e banco a partir de checkout limpo pelo runbook.
- Liveness não depende do banco; readiness reflete dependências necessárias.
- Conteúdo-canário, query, secrets e raw IDs não aparecem em logs, traces ou labels após a suite E2E.
- Cada request possui correlation ID e duração sem expor payload.
- Métricas distinguem sucesso, validation, conflict, dependency failure e abstention.
- SIGTERM/shutdown encerra requests dentro do timeout e não perde transação confirmada.
- Outage de embedding/database produz erro/fallback especificado, sem retry storm.
- Migration e backup/restore são exercitados em ambiente descartável.
- Forget após restore respeita deletion ledger/política definida por W07.

## Testes

- startup/shutdown/restart e readiness transitions;
- dependency timeout, retry e circuit/fallback behavior;
- log/trace canary scan;
- cardinality budget test;
- migration deploy/rollback simulation;
- backup/restore/delete retention;
- load smoke para latência e pool exhaustion;
- duplicated scheduled run/idempotent worker.

## Riscos e mitigação

- **Observabilidade vaza memória:** allowlist de campos e canary scan.
- **Stack operacional supera produto:** exporters opcionais, defaults simples.
- **Retries duplicam escrita:** somente idempotent operations com keys.
- **Health mascara falha:** separar liveness/readiness e testar degradação.
- **Backups quebram forget:** retenção limitada e reaplicação de deletion ledger sem conteúdo.
- **Métricas com cardinalidade explosiva:** buckets e labels fechadas.

## Handoff

Entregar a W09 comandos status/smoke; a W12 setup e runbooks revisados; a W08 metrics/budgets observados. Para alpha, declarar exatamente qual deployment foi testado e quais topologias não são suportadas.

## Perfil sugerido do executor

P2 com experiência em operação Python/Postgres, OpenTelemetry, containers e failure handling. Revisão P4 obrigatória para redaction, retention e backup/delete.
