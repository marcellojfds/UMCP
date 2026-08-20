# W03 — Storage e migrations

## Objetivo

Implementar persistência transacional do modelo canônico em PostgreSQL + pgvector, com migrations reproduzíveis, isolamento por owner, histórico, relações e forget verificável. O storage deve servir aos use cases sem vazar SQL ou detalhes de vetor para o domínio.

## Contexto mínimo

OMP começa com um único banco para dados estruturados, relações e embeddings. A escolha reduz complexidade operacional e mantém abertas otimizações futuras. O banco precisa suportar o MVP 0 e não antecipar graph database, sharding ou múltiplos stores.

Leia W00, W01, W02, W06, W07 e W11.

## Escopo

### Dentro

- desenho relacional e DDL;
- migrations forward e downgrade quando seguro;
- implementação dos repository/unit-of-work ports de W02;
- transações, optimistic concurrency e idempotência;
- persistência de versões, provenance, relations e embeddings;
- constraints, indexes e filtragem por owner/space/state;
- cascade de forget;
- seed sintético mínimo e ambiente de banco para testes;
- medição inicial de planos/latência de queries.

### Fora

- definição do aggregate e state machine, owned por W02;
- algoritmo de embedding, candidate retrieval e ranking, owned por W06;
- schemas e erros MCP, owned por W04;
- criptografia client-side, owned por W07/W09;
- backups, dashboards e runtime, owned por W11;
- política de import/export, owned por W09.

## Decisões já tomadas

- PostgreSQL com extensão pgvector é o único store primário do MVP.
- Todas as consultas e uniqueness rules incluem `owner_id`; `space` é filtro lógico opcional.
- Conteúdo, metadados sensíveis e vetores nunca aparecem em logs de query da aplicação.
- O schema distingue memória, versões/proveniência, relações e embedding descriptor.
- Relações usam tabelas relacionais; graph database está fora.
- Forget remove conteúdo, versões, embeddings e relações conforme contrato W02/W07 numa única operação transacional.
- Migrations são a única forma suportada de mudar schema.

## Decisões abertas

- biblioteca de acesso e migrations, coordenada com W01;
- formato exato das tabelas após freeze de W02;
- uma tabela de versões versus snapshot/event hybrid;
- índice pgvector inicial e parâmetros, definidos com benchmarks W06;
- dimensão fixa do vetor e estratégia de troca de embedding;
- uso de Row Level Security no modo local e requisito antes de hosting.

Antes do Gate A, W03 e W06 devem registrar um embedding profile: provider lógico, model identifier, dimensão, versão de normalização e distance metric. Trocar profile exige re-embedding explícito, nunca mistura silenciosa no mesmo índice.

## Dependências

- W01: configuração, async strategy e ports.
- W02: schema, invariantes, idempotência e forget.
- W06: embedding profile e padrões de consulta.
- W07: data classification e retenção.

W04, W05, W06, W09, W10 e W11 dependem da implementação concreta desta frente.

## Entregáveis

- diagrama/schema relacional documentado;
- migration inicial e migrations incrementais;
- repositories e unit of work;
- setup da extensão pgvector;
- constraints e indexes justificados por query patterns;
- integration tests contra Postgres real descartável;
- procedimento de migration, rollback e re-embedding;
- benchmark baseline com corpus sintético versionado.

## Etapas

1. Mapear o modelo W02 para tabelas sem alterar suas semânticas.
2. Validar profile e query patterns com W06.
3. Escrever migration inicial, constraints e indexes básicos.
4. Implementar repositories e transações.
5. Cobrir concorrência, idempotência, isolamento e forget.
6. Medir plano/latência com corpus pequeno e um corpus de escala-alvo documentada.
7. Testar banco vazio, upgrade, downgrade seguro e reconstrução de índice.

## Critérios de aceite verificáveis

- Banco vazio chega ao head das migrations por um único comando documentado.
- Schema resultante corresponde ao modelo W02 e falha em constraints inválidas.
- Repositories passam a suíte de contrato usando Postgres real.
- Duas gravações concorrentes com a mesma idempotency key resultam em uma memória.
- Update stale não perde dados e retorna conflito detectável pelo application service.
- Toda query de memória exige owner; testes provam que owner A não lê ou altera owner B.
- Forget elimina todas as linhas/content blobs/vetores cobertos pelo contrato e é idempotente.
- Uma migration down/up em banco descartável preserva o que o procedimento declara preservar.
- `EXPLAIN` dos query patterns críticos usa os indexes esperados no dataset de benchmark.

## Testes e benchmarks

- integration/contract tests para cada método de repository;
- corrida de create/update e idempotency;
- cascade de forget e limpeza de relações;
- filtros combinados owner/space/type/state/time;
- incompatibilidade de embedding profile;
- migration smoke desde zero e desde snapshot da versão anterior;
- benchmark p50/p95 da busca candidata em volumes declarados, sem fixar SLO comercial prematuro.

## Riscos e mitigação

- **Dimensão de embedding vira lock-in:** profile explícito e job de re-embedding planejado.
- **Owner filter esquecido:** repository exige owner na assinatura e contract tests cross-owner.
- **Histórico cresce sem limite:** medir e definir retenção somente com W07, sem apagar por conveniência.
- **Index tuning prematuro:** escolher com dados W06 e preservar baseline exato.
- **Forget deixa cópias:** teste de cascade e runbook de backups em W11.

## Handoff

Entregar a W04/W05/W06/W10 repositories estáveis, transaction semantics, erros e fixture factory. Entregar a W11 migrations/runbooks e sinais operacionais. Informar profile de embedding, volumes medidos e limitações do índice.

## Perfil sugerido do executor

P2 com domínio de PostgreSQL, pgvector, migrations, transações e async Python. Revisão P4 para isolamento/forget e revisão P3 com W06 para índice vetorial.
