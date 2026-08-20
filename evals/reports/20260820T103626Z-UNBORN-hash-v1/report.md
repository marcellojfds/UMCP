# S04 retrieval evaluation — hash/v1

Decision: **NO-GO**

## Gate metrics

| Metric | Result | Gate |
| --- | ---: | ---: |
| precision@5 | 0.000 | >= 0.800 |
| intrusion@5 | 0.000 | <= 0.100 |
| abstention | 1.000 | >= 0.900 |
| lifecycle/isolation | 1.000 | 1.000 |
| p95 (ms) | 20.695 | < 2500 |

## Reasons

- precision_at_5 < 0.80
- red positive slice query_kind=cross_domain
- red positive slice query_kind=positive

Failure details are identifiers only in `report.json`; no corpus content is copied here.
