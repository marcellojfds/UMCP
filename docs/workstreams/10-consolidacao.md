# W10 — Consolidação de conhecimento

## Objetivo

Transformar conjuntos de memórias em propostas de conhecimento de nível mais alto, mantendo evidence, auditabilidade, idempotência e possibilidade de rejeição. Esta frente começa apenas no MVP 3 e não é um summarizer de histórico de conversa.

## Contexto mínimo

Consolidação revisita memórias ao longo do tempo, encontra padrões e cria abstrações. MCP não agenda tarefas; execução periódica acontece em worker/cron/scheduled job externo. Uma conclusão genérica ou sem suporte é pior que não consolidar.

Leia W00, W02, W03, W05, W06, W07, W08 e W11.

## Escopo

### Dentro

- seleção e agrupamento de memórias elegíveis;
- contrato de consolidation run e checkpoints;
- geração/validação de proposed derived memory;
- evidence graph usando relations `derived_from`/`supports`;
- dedupe de consolidações e idempotência;
- estados `proposed|accepted|rejected` da execução, sem confundir com memory state;
- triggers `on-demand`, após N memórias e scheduled external;
- budgets, failure handling e eval com W08.

### Fora

- scheduler embutido no MCP;
- graph database;
- alteração destrutiva automática de memórias-fonte;
- state machine base, owned por W02;
- infraestrutura do worker, owned por W11;
- UI de revisão;
- aprendizado/treino de modelos.

## Decisões já tomadas

- Consolidação não bloqueia MVP 0–2.
- Primeira versão produz propostas; promoção automática vem desligada.
- Toda memória derivada aponta para uma ou mais memórias/evidências existentes.
- Sources permanecem acessíveis e não são superseded/archived apenas porque foram consolidadas.
- Reexecução com mesmo input set, policy e model version é idempotente.
- Output registra source IDs/versions, prompt/policy/model version e timestamp.
- Scheduler é externo; worker expõe operação idempotente/on-demand.
- O processo pode decidir não produzir consolidação.

## Decisões abertas

- eligibility window e trigger;
- clustering por embedding, relation, type/space/time ou combinação;
- mínimo/máximo de sources;
- granularidade de derived insight e types permitidos;
- revisão humana sem UI dedicada;
- critérios para aceitar, rejeitar ou substituir proposal;
- tratamento de source que depois é forgotten/contradicted;
- cadence e budgets operacionais.

## Dependências

- Gate D concluído ou justificativa explícita para usar apenas baseline.
- W02: derived relations e provenance.
- W03: transactions/query support.
- W05: policy patterns e provider abstraction, quando reutilizável.
- W08: dataset/rubric.
- W11: worker/scheduling.

W04 só expõe `memory.consolidate` se houver caso de uso público aprovado; execução administrativa pode permanecer fora do MCP v0.

## Entregáveis

- spec de consolidation run/proposal;
- selector/clusterer e consolidator atrás de interfaces;
- worker operation idempotente;
- evidence binding e invalidation policy;
- proposal review path via CLI/admin interface mínima;
- fixtures e eval report Gate E;
- runbook de schedule/retry/checkpoint.

## Etapas

1. Definir rubric e corpus com W08 antes do prompt/algoritmo.
2. Implementar selector determinístico e dry-run.
3. Gerar propostas estruturadas com evidence references.
4. Validar cada claim contra sources e rejeitar output inválido.
5. Persistir run/proposal de forma idempotente, sem alterar sources.
6. Expor accept/reject por interface administrativa mínima.
7. Medir qualidade/custo e somente então discutir promoção automática.

## Critérios de aceite verificáveis

- Run sem grupo elegível termina com zero proposals e status de sucesso.
- Toda frase factual de uma proposal é suportada por source version rastreável.
- Source set/model/policy iguais não geram proposal duplicada.
- Falha parcial pode ser retomada sem duplicar efeitos.
- Accept cria memória derivada válida e relations; reject não cria memória.
- Forget/contradiction de source dispara policy documentada de invalidation/review.
- Gate E: factual support = 1,00 em casos críticos, acceptance humana >= 0,75, generic output <= 0,10 e idempotência = 100%.
- Promotion automática permanece off no primeiro release da feature.

## Testes e evals

- unit de eligibility, clustering, idempotency key e evidence binding;
- integration de checkpoint/retry/transaction;
- sources contraditórias, redundantes, cross-space e com versions antigas;
- prompt injection em source content;
- rubrics de factual support, novelty, usefulness e specificity;
- comparação com simple summarization baseline;
- custo/latência por source e por proposal.

## Riscos e mitigação

- **Resumo genérico vira conhecimento:** rubric de novelty/specificity e reject path.
- **Hallucination:** claim-evidence binding e factual support gate.
- **Loop recursivo de consolidação:** depth/lineage limit e eligibility rule.
- **Source muda ou some:** invalidation policy e version pinning.
- **Jobs duplicados:** deterministic run key/checkpoints.
- **Custo crescente:** limits, dry-run e schedule por benefício medido.

## Handoff

Entregar a W11 worker contract/schedule/runbook; a W08 outputs/configs; a W02 qualquer extensão de domain proposta antes de implementá-la; a W12 limites e exemplos honestos. Registrar como proposals são revisadas sem UI.

## Perfil sugerido do executor

P3 com experiência em clustering, structured generation, provenance e evals de summarization/abstraction; P2 para jobs/idempotência e revisão P4 para data handling.
