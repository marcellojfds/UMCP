# W06 — Retrieval e reranking

## Objetivo

Recuperar poucas memórias que materialmente ajudam o contexto atual, com scores explicáveis e abstention confiável. A frente entrega um baseline vetorial no MVP 0 e só adiciona query expansion/reranking no MVP 2 quando evals mostrarem ganho.

## Contexto mínimo

Busca por similaridade é necessária, mas não suficiente para o objetivo cross-domain. Os sinais candidatos incluem similaridade, importance, confidence, recency, type, space/project relevance, relations, state e utilidade histórica. Intrusion rate é tão importante quanto recall.

Leia W00, W02, W03, W04, W07 e W08.

## Escopo

### Dentro

- embedding provider port e profile versioning;
- interpretação de query e candidate generation;
- filtros e busca vetorial baseline;
- normalização de sinais, ranking e thresholds;
- abstention e `reason_retrieved`;
- experimentos de query expansion e reranking;
- lógica de memórias relacionadas explícitas/inferidas;
- budgets de candidates, latência e chamadas de modelo;
- diagnóstico offline com W08.

### Fora

- DDL/index implementation, owned por W03;
- schemas `memory.search`/`memory.related`, owned por W04;
- seleção/escrita de memória, owned por W05;
- definição de states/relations, owned por W02;
- consolidação, owned por W10;
- contexto final ou resposta do modelo consumidor.

## Decisões já tomadas

- MVP 0: embedding único versionado, busca vetorial, filtros, score simples e threshold.
- Default de busca considera apenas `active`; outros states exigem filtro explícito.
- Todas as buscas são isoladas por owner antes do ranking.
- Search pode e deve retornar lista vazia.
- `reason_retrieved` descreve sinais/relação sem revelar chain-of-thought nem dados fora da memória retornada.
- Importance/confidence não resgatam candidato semanticamente irrelevante sozinhos.
- Query expansion e LLM reranking ficam desligados até comparação no Gate D.
- Score público é normalizado e não promete comparabilidade entre profile versions.

## Baseline proposto

```text
query
 -> validação e filtros
 -> embedding conforme profile
 -> top-N candidatos por distância dentro do owner
 -> remoção por state/threshold
 -> combinação calibrada de similaridade + importance + confidence
 -> top-K ou lista vazia
 -> reason_retrieved determinístico
```

Recency pode ser sinal secundário e dependente do tipo; não deve apagar insights duráveis apenas por idade.

## Decisões abertas

- provedor/modelo, dimensão e distance metric do embedding;
- ANN index e parâmetros com W03;
- fórmula/pesos e calibração de score;
- thresholds global versus por type/space;
- candidate N e return K defaults;
- query expansion determinística versus model-based;
- reranker cross-encoder/LLM e fallback;
- uso de relations e historical usefulness;
- contrato e momento de `memory.related`.

## Dependências

- W01: ports/configuração.
- W02: filtros, state e relations.
- W03: store vetorial e query patterns.
- W07: exposição de embeddings e provider policy.
- W08: corpora, labels e gates.

W04 e W09 consomem search/related application services.

## Entregáveis

### MVP 0

- embedding profile e adapter;
- baseline candidate retrieval/ranking/abstention;
- explicação determinística do resultado;
- unit/integration tests e relatório baseline.

### MVP 2

- runners comparáveis para vector-only, expansion e reranking;
- implementação selecionada atrás de feature flags;
- fallback sem modelo e budgets;
- `related` use case, se aprovado;
- relatório Gate D com cross-domain e intrusion.

## Etapas

1. Fixar dataset/queries W08 antes de calibrar.
2. Escolher embedding profile e validar com W03.
3. Implementar vector-only + filtros + abstention.
4. Medir por type, negative query e cross-domain.
5. Após Gate B, implementar abordagens avançadas isoladas.
6. Comparar ganho, custo, latência e falhas; selecionar a mais simples que atenda o gate.
7. Calibrar thresholds em validation set e confirmar em holdout.

## Critérios de aceite verificáveis

- Query de owner A nunca gera candidato de owner B.
- States não ativos ficam fora do default.
- Caso negativo canônico retorna zero resultados.
- Resultado contém score/profile/reason coerentes e ordenação estável quando scores empatam.
- Mudança de embedding profile não mistura vetores incompatíveis.
- Baseline atende no conjunto inicial: precision@5 >= 0,80, intrusion@5 <= 0,10 e negative-query abstention >= 0,90; amostra e incerteza devem ser publicadas.
- Gate D exige que abordagem avançada melhore a métrica de utilidade/cross-domain predefinida sem piorar intrusion além de 0,02 absoluto nem ultrapassar budgets aceitos.
- Timeout/erro de reranker usa fallback documentado e não injeta memória de baixa confiança.

## Testes e evals

- unit de score normalization, threshold, tie-break e reason;
- integration com pgvector real e profiles incompatíveis;
- corpus com relevant, hard negatives, stale, contradicted e cross-domain;
- precision@K, recall@K, MRR/nDCG quando úteis, intrusion, abstention, latência e custo;
- ablations por sinal;
- adversarial queries para palavras iguais em contextos diferentes;
- comparação com `no memory` e `vector-only` nos cenários de resposta final.

## Riscos e mitigação

- **Otimizar similaridade, não utilidade:** judgments de impacto e cenários cross-domain.
- **Recall agressivo destrói confiança:** threshold/abstention e intrusion gate.
- **LLM reranker não determinístico:** versionamento, fixtures e fallback.
- **Score enganoso:** documentar semântica/profile, não vender como probabilidade absoluta.
- **Embedding vaza semântica:** coordenar com W07 e não alegar privacidade forte.
- **Overfit:** validation/holdout e casos adicionados a partir de falhas reais.

## Handoff

Entregar a W03 profile/query patterns; a W04 schemas de resultado e errors; a W08 configs, outputs e relatório; a W11 métricas/budgets; a W09 exemplos de abstention. Separar claramente baseline aprovado de experimentos feature-flagged.

## Perfil sugerido do executor

P3 com experiência em information retrieval, embeddings, ranking, calibração e avaliação. Revisão P2 para integração pgvector e P4 para leakage por vetores.
