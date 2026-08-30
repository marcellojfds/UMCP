# Plano de evals — Alpha v0

> **Plano histórico.** Os relatórios executados estão em `evals/reports/`; o
> problema de retrieval atual está em [`known-issues.md`](known-issues.md) e a
> remediação ativa em [`roadmap.md`](roadmap.md).

**Status histórico naquele momento:** aprovado para implementação, ainda não executado
**Gate alvo:** Gate B de retrieval
**Backend obrigatório:** PostgreSQL 16 + pgvector, sem fake/file como evidência

## 1. Objetivo e decisão produzida

O eval deve responder, de forma reproduzível, se o profile `hash/v1` atual é
adequado para o Alpha v0. O resultado possível é `GO`, `NO-GO` ou
`INCONCLUSIVE`; o runner não altera threshold, dataset ou produção para obter
um resultado verde.

O Gate B exige simultaneamente:

- `precision@5 >= 0,80` nas queries positivas;
- `intrusion@5 <= 0,10` em todos os resultados retornados;
- abstention em queries negativas `>= 0,90`;
- lifecycle e owner isolation `= 100%` nos casos determinísticos;
- configuração, amostra, slices e p50/p95 publicados;
- zero conteúdo proibido em logs e artifacts operacionais.

## 2. Estrutura a implementar

```text
evals/
  README.md
  datasets/retrieval-v0/
    datasheet.md
    memories.jsonl
    queries.jsonl
    relevance.jsonl
    checksums.json
  configs/hash-v1.yaml
  rubrics/retrieval-v0.md
  reports/.gitkeep
src/omp/evals/
  dataset.py
  metrics.py
  runner.py
tests/evals/
  test_dataset.py
  test_metrics.py
  test_runner.py
```

Relatórios gerados não devem ser sobrescritos silenciosamente. O relatório
canônico do RC será versionado em `evals/reports/<data>-<revision>-hash-v1/`
com `report.json`, `report.md` e checksums.

## 3. Corpus `retrieval-v0`

O corpus será inteiramente sintético e escrito antes de qualquer tuning:

- 25 episódios coerentes de usuários fictícios;
- pelo menos 100 memórias;
- 50 queries: 35 positivas e 15 negativas;
- pelo menos 10 casos cross-domain com baixo overlap lexical;
- hard negatives com vocabulário semelhante e intenção diferente;
- mudanças de decisão/preferência, duplicatas, contradições, estados não
  ativos, owners e spaces distintos;
- cenário canônico `MBA market density -> estratégia GTM`.

Split fixo por episódio, nunca por linha: `development` com 20 episódios e
`holdout` com 5. O holdout deve conter pelo menos 10 queries, 3 negativas e 2
cross-domain. Um episódio não pode aparecer em mais de um split.

### Schemas mínimos

Cada memória registra `memory_id`, `episode_id`, `split`, `owner_id`, `space`,
`type`, `state`, `content`, `importance`, `confidence` e provenance sintética.

Cada query registra `query_id`, `episode_id`, `split`, `owner_id`, `query`,
`filters`, `kind` (`positive`, `negative`, `cross_domain`, `hard_negative`) e
`expected_behavior` (`retrieve` ou `abstain`).

`relevance.jsonl` registra pares `query_id`/`memory_id`, grau `0..2` e motivo
curto baseado na rubric. Os IDs devem ser estáveis e não conter texto sensível.

## 4. Métricas congeladas

- `precision@5`: para queries positivas, memórias relevantes entre os cinco
  primeiros resultados dividido pelos resultados retornados até cinco. Query
  positiva com zero resultados recebe zero.
- `intrusion@5`: resultados explicitamente rotulados como irrelevantes ou hard
  negatives divididos por todos os resultados retornados até cinco. Violação
  de owner/state/profile também falha o gate determinístico, mesmo que a média
  permaneça abaixo de 0,10.
- `abstention_rate`: queries negativas que retornam zero resultados divididas
  pelo total de queries negativas.
- `lifecycle_isolation_correctness`: checks determinísticos aprovados dividido
  pelo total; qualquer falha resulta em `NO-GO`.
- latência: p50 e p95 end-to-end após warm-up, com hardware e número de runs
  registrados. Para `hash/v1`, custo externo esperado é zero, mas deve ser
  registrado explicitamente.

As métricas também serão mostradas por split, query kind, memory type, space e
estado. A média agregada não pode esconder um slice determinístico vermelho.

## 5. Caminho de execução

1. Validar schemas, IDs, checksums, contagens e ausência de leakage entre
   splits.
2. Subir o ambiente pinado de `ops/postgres/compose.yaml` e aplicar migrations.
3. Importar somente o split selecionado pelo application service real.
4. Executar buscas pelo mesmo gateway usado pelo MCP, com threshold `0.78` e
   `limit=5`.
5. Executar checks de owner, state, space, profile e abstention.
6. Calcular métricas em funções puras cobertas por exemplos manuais.
7. Gerar JSON primeiro e Markdown a partir dele.
8. Executar scan de canário/secrets sobre stdout, stderr e artifacts.
9. Repetir o relatório do mesmo commit para confirmar determinismo.

Um subconjunto pequeno e determinístico deve rodar em toda PR. O corpus completo
roda manualmente, por schedule e obrigatoriamente no release candidate.

## 6. Metadados obrigatórios do relatório

- revisão Git e estado dirty/clean;
- dataset/config version e SHA-256;
- Python, OMP, PostgreSQL, pgvector e dependências relevantes;
- profile/dimensão, threshold, candidate limit e result limit;
- tamanho de cada split/slice;
- métricas agregadas e por slice;
- p50/p95, número de warm-ups/runs e descrição do ambiente;
- lista de failure IDs sem copiar conteúdo integral;
- decisão `GO`, `NO-GO` ou `INCONCLUSIVE` e razões objetivas.

## 7. Regras contra Goodhart e leakage

- O holdout não pode ser lido durante tuning de threshold/profile.
- Mudança no corpus cria nova versão; resultados antigos permanecem.
- Target só muda por ADR com comparação antes/depois.
- Falhas reais entram primeiro no development; promoção ao holdout ocorre em
  uma versão futura e registrada.
- Dados pessoais reais são proibidos neste Alpha sem consentimento e revisão
  de privacidade separados.
- LLM-as-judge não participa do Gate B baseline.

## 8. Decisões ainda exigidas do mantenedor

- Aprovar o budget provisório de busca: p95 menor que `2.500 ms`, alinhado ao
  timeout público, em runner local single-client após warm-up.
- Confirmar que `GO` exige também que nenhum slice positivo com pelo menos
  cinco queries fique abaixo de `precision@5 = 0,60`.
- Se `hash/v1` falhar, escolher entre adotar outro embedding por ADR ou publicar
  apenas como engineering preview; baixar o gate não é uma opção automática.

## 9. Definition of Done da implementação

- `python -m omp.evals.runner --config evals/configs/hash-v1.yaml` reconstrói o
  relatório em checkout limpo;
- testes do dataset, métricas e runner estão verdes;
- CI regression subset falha de maneira explícita sem PostgreSQL;
- relatório full e checksums são reproduzíveis;
- um revisor que não escreveu o corpus revisa labels e ao menos 20% dos pares;
- o mantenedor registra a decisão Gate B com link para o relatório.
