# T03 — E5 development promotion eligibility

**Decision:** **development promotion eligible**. This is not Gate B GO; the
holdout remains prohibited pending a separate authorization.

After the authorized 384d persistence correction, the regression test covered
semantic create/update/import, stale-vector exclusion after a concurrent
version change, the `source_version >= 1` invariant and unchanged hash/v1 64d
storage. It passed after zero-to-head migration on the confirmed disposable
`omp_test` compose database.

The newly authorized validation epoch then ran exactly once per path on the
same corrected code and frozen configuration:

| Path | precision@5 | intrusion@5 | abstention | lifecycle/isolation | p95 ms | Result |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Harness | 0.899 | 0.000 | 1.000 | 1.000 | 44.020 | pass |
| PostgreSQL/gateway | 0.899 | 0.000 | 1.000 | 1.000 | 254.758 | pass |

The paths returned identical IDs across 40 development queries. Forty-four
returned scores compared within the documented tolerance, with a maximum
decimal delta of `0.000001`. The two source reports and a checksummed
equivalence artifact are preserved under `evals/reports/`; only IDs/scores are
stored and every artifact has `holdout_executed=false`.

The frozen candidate remains `intfloat/e5-small-v2` revision
`ffb93f3bd4047442299a41ebb6fa998a38507c52`, mean pooling,
`query:`/`passage:`, 384d, threshold 0.76, candidate limit 50 and result limit
5. No BGE promotion, hybrid, model acquisition, stage, commit, push, PR,
remote action or holdout execution occurred. The disposable compose service was
removed.
