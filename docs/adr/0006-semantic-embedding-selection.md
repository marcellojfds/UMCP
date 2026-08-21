# ADR 0006 — Seleção experimental de embedding semântico

**Status:** NO-GO corrigido; nenhuma seleção de produção autorizada.

## Contexto

S04 registrou `hash/v1` com `precision@5 = 0.000` no threshold congelado
`0.78`. S08 comparou exatamente dois modelos locais pequenos sobre o corpus
congelado e avaliou somente `development`. A primeira execução armazenava
`passage_prefix`, mas não o aplicava; ela é histórica e não é evidência de
seleção. A execução corrigida aplica os prefixos explícitos `query:` e
`passage:` e é a única base para a decisão abaixo.

Dataset preservado, com os mesmos checksums de S04:

| Arquivo | SHA-256 |
| --- | --- |
| `memories.jsonl` | `30135468f0a2ec4f1539d7f53c2175267ba77962a65b3694e86809d3e380df98` |
| `queries.jsonl` | `114b9dfb1f7cebe41334539ff14eda1741bc7bd0f967fee760ba8c020f6d9068` |
| `relevance.jsonl` | `8fec0e7f42caad36e4a1a6f2d3d078ac94bcff6e62c625cb230e3f5dc3e96a9c` |

## Resultado corrigido

| Modelo | Revisão | Dimensão | Prefixos | precision@5 | intrusion | abstention | lifecycle/isolation | p95 ms | Resultado |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | --- |
| all-MiniLM-L6-v2 | `1110a243fdf4706b3f48f1d95db1a4f5529b4d41` | 384 | none/none | 0.000 | 0.000 | 1.000 | 1.000 | 10.675 | NO-GO |
| e5-small-v2 | `ffb93f3bd4047442299a41ebb6fa998a38507c52` | 384 | query:/passage: | 0.756 | 0.000 | 1.000 | 1.000 | 15.932 | NO-GO |

O gate exige `precision@5 >= 0.800`; E5 falha por 0.044. O holdout não foi
executado e não foi usado para escolha ou tuning. Nenhum terceiro modelo foi
introduzido silenciosamente.

Relatório canônico corrigido:
[`report.json`](../../evals/reports/20260820T190703Z-4947ebfb3789-semantic-development/report.json).

## Consequência

Não existe candidato semântico aprovado para S09. Uma nova seleção precisa de
uma experiência separada e explicitamente autorizada, com modelo/revisão
pinados, checksums e o mesmo protocolo. Até lá, o provider de produção padrão
continua sendo `hash/v1`; o provider E5 e a migration 384d permanecem código
experimental e não autorizam Gate B ou holdout.
