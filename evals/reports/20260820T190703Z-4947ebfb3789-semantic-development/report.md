# S08 semantic embedding comparison

Decision: **NO-GO**

Only `development` was evaluated. The holdout was not executed.

| Candidate | precision@5 | intrusion@5 | abstention | lifecycle/isolation | p50 / p95 (ms) | Result |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| sentence-transformers/all-MiniLM-L6-v2 | 0.000 | 0.000 | 1.000 | 1.000 | 8.338 / 10.675 | NO-GO |
| intfloat/e5-small-v2 | 0.756 | 0.000 | 1.000 | 1.000 | 14.951 / 15.932 | NO-GO |

## Decision reasons

- NO-GO: zero or multiple candidates satisfy the development gates; no selection is valid
