# T02 — E5 promotion validation at frozen threshold 0.76

**Decision:** **NO-GO**. Holdout remains closed.

## Frozen candidate

The maintainer selected E5 for operational maturity, not statistical
superiority: `intfloat/e5-small-v2` at
`ffb93f3bd4047442299a41ebb6fa998a38507c52`, mean pooling, `query:`/`passage:`
prefixes, dimension 384, profile `semantic/e5-small-v2-s09`, candidate limit
50 and result limit 5. ADR 0008 recorded the median rule before execution;
the frozen production threshold is `0.76`.

## Development-only validation

| Path | precision@5 | intrusion@5 | abstention | lifecycle/isolation | p95 ms | Result |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Corrected local harness | 0.899 | 0.000 | 1.000 | 1.000 | 127.290 | GO |
| PostgreSQL/repository/application/gateway | not measured | not measured | not measured | not measured | not measured | NO-GO |

The harness result is preserved at
[`20260820T203526Z-4947ebfb3789-semantic-development`](../../../evals/reports/20260820T203526Z-4947ebfb3789-semantic-development/), with
`holdout_executed=false` and checksums. It includes a sanitized 40-query
identifier/score trace for later equivalence verification.

## Protocol deviation recorded

The first harness invocation under the frozen configuration produced the
preserved artifact `20260820T203327Z-4947ebfb3789-semantic-development`. Before
the PostgreSQL path, the harness and runner were changed only to emit the
identifier/score trace required for the authorized cross-path comparison, then
the identical frozen configuration was rerun as
`20260820T203526Z-4947ebfb3789-semantic-development`. This did not vary model,
revision, threshold, corpus, labels or gates, but it means this work cannot be
presented as a literal single executable validation over unchanged code. The
later artifact is used only as diagnostic evidence; the PostgreSQL failure
independently makes promotion NO-GO.

The real path used the confirmed disposable PostgreSQL 16.15 compose service,
applied migration head `0004_semantic_source_version`, and failed at the first
development fixture write. `PostgresMemoryRepository.create` called
`_embedding_values` without supplying required semantic `source_version`.
The database rejected the insert before any query, metric or equivalence result
could exist. The sanitized failure artifact is
[`20260820T203648Z-4947ebfb3789-e5-small-v2-s09-development-postgres`](../../../evals/reports/20260820T203648Z-4947ebfb3789-e5-small-v2-s09-development-postgres/), with
`holdout_executed=false` and checksums.

## Consequence

The required two-path promotion condition is not met. This is an
implementation NO-GO, not permission to retune `0.76`, promote BGE, run a
hybrid, acquire another model or access holdout. The disposable compose service
was removed. No stage, commit, push, PR or GitHub action occurred.
