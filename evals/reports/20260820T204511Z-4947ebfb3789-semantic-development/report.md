# S08 semantic embedding comparison

Decision: **GO-CANDIDATE**

Only `development` was evaluated. The holdout was not executed.

| Candidate | precision@5 | intrusion@5 | abstention | lifecycle/isolation | p50 / p95 (ms) | Result |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| intfloat/e5-small-v2 | 0.899 | 0.000 | 1.000 | 1.000 | 18.927 / 44.020 | GO |

## Decision reasons

- selected intfloat/e5-small-v2: sole candidate satisfying every development gate
