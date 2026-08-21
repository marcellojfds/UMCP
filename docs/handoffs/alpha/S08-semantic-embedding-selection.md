# S08 handoff — seleção de embedding semântico

## Decisão

**NO-GO para avançar ao holdout ou declarar um candidato S09.** A execução
anterior tinha um erro no harness: o campo `passage_prefix` era configurado,
mas não era aplicado ao texto das passagens. A execução corrigida aplica
`query:` e `passage:` explicitamente aos dois candidatos, preserva o threshold
`0.78` e avalia somente `development`.

## Comparação corrigida

| Modelo | Revision | precision@5 | intrusion@5 | abstention | lifecycle/isolation | p50/p95 ms | Decisão |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| `sentence-transformers/all-MiniLM-L6-v2` | `1110a243fdf4706b3f48f1d95db1a4f5529b4d41` | 0.000 | 0.000 | 1.000 | 1.000 | 8.338 / 10.675 | NO-GO |
| `intfloat/e5-small-v2` | `ffb93f3bd4047442299a41ebb6fa998a38507c52` | 0.756 | 0.000 | 1.000 | 1.000 | 14.951 / 15.932 | NO-GO |

E5 fica abaixo do gate `precision@5 >= 0.800`; as falhas são publicadas
somente pelos IDs `query-09-a`, `query-10-a`, `query-14-a`, `query-16-a`,
`query-18-a` e `query-20-a`. Nenhum terceiro modelo foi introduzido.

Referências:

- [ADR 0006](../../adr/0006-semantic-embedding-selection.md)
- [JSON corrigido](../../../evals/reports/20260820T190703Z-4947ebfb3789-semantic-development/report.json)
- [Markdown corrigido](../../../evals/reports/20260820T190703Z-4947ebfb3789-semantic-development/report.md)
- configs `evals/configs/semantic-*.yaml`
- harness `src/omp/evals/semantic_harness.py`

## Integridade e controles

O dataset `retrieval-v0` permaneceu byte-a-byte congelado; os SHA-256 de
`memories.jsonl`, `queries.jsonl` e `relevance.jsonl` permanecem iguais aos de
S04. Os relatórios `*-UNBORN-hash-v1` e os dois relatórios S08 anteriores foram
preservados. O holdout não foi lido nem executado. Artifacts contêm somente
IDs de falha e passaram o scan de secrets/canário.

## Bloqueio e próximo passo

O plano exige uma nova experiência autorizada quando a linha E5 falha, sem
baixar threshold, alterar corpus ou reutilizar o holdout para tuning. O
provider/migration local experimental já têm testes isolados, mas não podem
formar um RC enquanto development semântico estiver vermelho.

Não houve commit, push, tag ou publicação nesta sessão.
