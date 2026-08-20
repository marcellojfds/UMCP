# S04 handoff — retrieval evaluation `hash/v1`

## Decision

**NO-GO.** The frozen `retrieval-v0` corpus was not modified. The current
`hash/v1` baseline returns no result for all 35 positive queries at the frozen
threshold `0.78`, producing `precision@5 = 0.000`, below the `0.800` gate.
This is a quality failure, not a latency, cost, owner, lifecycle, state, or
profile-isolation failure.

Do not lower the threshold or change the corpus/profile to obtain a green
result. Create a separate ADR to compare semantic embedding alternatives and
a re-embedding migration; S04 did not implement another provider.

## Canonical report and reproduction

Canonical artifact:
`evals/reports/20260820T103626Z-UNBORN-hash-v1/`.

```sh
docker compose -f ops/postgres/compose.yaml up -d --wait
OMP_DATABASE_URL='postgresql+asyncpg://omp_test:omp_test@127.0.0.1:55433/omp_test' \
  python -m alembic upgrade head
OMP_DATABASE_URL='postgresql+asyncpg://omp_test:omp_test@127.0.0.1:55433/omp_test' \
  python -m omp.evals.runner --config evals/configs/hash-v1.yaml
```

The environment is PostgreSQL `16.15`, pgvector `0.8.6`, Python `3.11.8`, OMP
`0.1.0a1`, local single-client. Git has no commit yet (`UNBORN`) and was dirty;
that state is explicitly recorded in the JSON instead of being hidden.

## Results

| Metric | Result | Gate |
| --- | ---: | ---: |
| precision@5 | 0.000 | >= 0.800 |
| intrusion@5 | 0.000 | <= 0.100 |
| negative-query abstention | 1.000 | >= 0.900 |
| lifecycle/isolation/profile correctness | 1.000 (50/50) | 1.000 |
| p50 | 6.982 ms | reported |
| p95 | 20.695 ms | < 2,500 ms provisional |
| external cost | USD 0.00 | reported |

The run used 3 warm-up passes and 2 measured passes (100 measured searches),
dimension 64, candidate limit 50, result limit 5, and threshold 0.78. The
report publishes all split/query-kind/memory-type/space/state slices. Positive
and cross-domain positive slices are red and remain visible.

All 35 positive failure records are listed by query and memory IDs only in
`report.json`; no corpus content is copied into the report. There were no
deterministic owner/state/space/profile failures and no abstention failures.

## Integrity and repeatability

Dataset SHA-256 values match S03 exactly:

- `memories.jsonl`: `30135468f0a2ec4f1539d7f53c2175267ba77962a65b3694e86809d3e380df98`
- `queries.jsonl`: `114b9dfb1f7cebe41334539ff14eda1741bc7bd0f967fee760ba8c020f6d9068`
- `relevance.jsonl`: `8fec0e7f42caad36e4a1a6f2d3d078ac94bcff6e62c625cb230e3f5dc3e96a9c`
- config `hash-v1.yaml`: `0d71a8b349ba932fdc72619c5d3817e408a2edf86dda006daf3ed17104c2524a`

Canonical report checksums:

- `report.json`: `99f4182531d23b8a256424b0d52d9a65fcb28d5e9b6cfb3af28ade8a9d0b5b99`
- `report.md`: `ebd22fc4d38b74e2c43f183813fc349d60b5c2261842364e035a66aa42930d4d`

Two prior full runs (`20260820T103412Z` and `20260820T103459Z`) produced the
same gate metrics and decision. Latency varied normally (p95 4.824 ms and
9.723 ms); the final report regenerated after the failure-ID reporting change
also remained well below the provisional budget.

Canary/secret-pattern scan of all generated report artifacts passed with no
matches. Unit validation passed: `7 passed`; Ruff and mypy for `omp.evals`
passed. No commit or push was performed.
