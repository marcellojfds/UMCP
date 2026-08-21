# S08 semantic embedding comparison

Decision: **NO-GO**

Only `development` was evaluated. The holdout was not executed.

| Candidate | precision@5 | intrusion@5 | abstention | lifecycle/isolation | p50 / p95 (ms) | Result |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| intfloat/e5-small-v2 | 0.756 | 0.000 | 1.000 | 1.000 | 15.510 / 22.976 | NO-GO |
| BAAI/bge-small-en-v1.5 | 0.000 | 0.000 | 1.000 | 1.000 | 18.536 / 44.248 | NO-GO |

## Decision reasons

- NO-GO: zero or multiple candidates satisfy the development gates; no selection is valid
