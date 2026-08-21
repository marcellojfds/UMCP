# S08-R3 handoff — BGE semantic development

## Decision

**NO-GO.** This was a separately authorized development-only experiment after
the corrected E5 NO-GO. It does not authorize runtime, PostgreSQL/gateway, or
holdout integration.

## Frozen protocol

- Model: `BAAI/bge-small-en-v1.5`
- Revision: `baab320e3049c6c62dd63560765566dd9083985e`
- Dimension/metric: `384` / cosine
- Pooling: normalized `[CLS]` from `last_hidden_state[:, 0, :]`
- Query instruction: `Represent this sentence for searching relevant passages: `
- Passage instruction: none
- Threshold: `0.78`
- Dataset: unchanged `retrieval-v0`; development only; holdout not read
- License: MIT; safetensors SHA-256
  `3c9f31665447c8911517620762200d2245a2518d6e7208acc78cd9db317e21ad`

## Development result

| precision@5 | intrusion@5 | abstention | lifecycle/isolation | p95 ms | Decision |
| ---: | ---: | ---: | ---: | ---: | --- |
| 0.000 | 0.000 | 1.000 | 1.000 | 20.788 | NO-GO |

The 28 positive development queries returned no result at the frozen
threshold. The canonical harness report contains only identifiers for failure
details and is preserved at
[`evals/reports/20260820T193539Z-4947ebfb3789-semantic-development/`](../../../evals/reports/20260820T193539Z-4947ebfb3789-semantic-development/).

The model cache and acquisition manifest remain outside the repository at
`/private/tmp/omp-bge-small-en-v1.5`; weights were not committed or packaged.
The holdout remains sealed. No commit, push, tag, release, or remote setting
change was performed.
