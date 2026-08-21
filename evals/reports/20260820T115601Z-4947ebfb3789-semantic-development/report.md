# S08 semantic embedding comparison

Decision: **GO-CANDIDATE**

Only `development` was evaluated. The holdout was not executed.

| Candidate | precision@5 | intrusion@5 | abstention | lifecycle/isolation | p50 / p95 (ms) | Result |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| sentence-transformers/all-MiniLM-L6-v2 | 0.000 | 0.000 | 1.000 | 1.000 | 11.385 / 29.146 | NO-GO |
| intfloat/e5-small-v2 | 0.875 | 0.000 | 1.000 | 1.000 | 25.713 / 52.269 | GO |

## Decision reasons

- selected intfloat/e5-small-v2: sole candidate satisfying every development gate
