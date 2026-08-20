# S03 handoff — retrieval-v0 dataset

## Delivered

Frozen synthetic corpus `evals/datasets/retrieval-v0`, datasheet, relevance
rubric, checksum manifest, offline schema/consistency validator, and validator
tests. No retrieval runner, metrics, database setup, embedding/profile change,
threshold change, or production-code change was made.

## Counts and slices

| Slice | Development | Holdout | Total |
| --- | ---: | ---: | ---: |
| Episodes | 20 | 5 | 25 |
| Memories | 100 | 25 | 125 |
| Queries | 40 | 10 | 50 |
| Retrieve / positive behavior | 28 | 7 | 35 |
| Abstain / negative behavior | 12 | 3 | 15 |
| Cross-domain | 8 | 2 | 10 |
| Relevance pairs | 68 | 17 | 85 |

Memory states: active 75, archived 25, superseded 13, contradicted 12.
Memory types: decision 36, fact 29, open question 25, preference 14, insight
11, lesson 10. There are 25 spaces and 25 opaque synthetic owners.

## Integrity

SHA-256 (exact JSONL bytes):

- `memories.jsonl`: `30135468f0a2ec4f1539d7f53c2175267ba77962a65b3694e86809d3e380df98`
- `queries.jsonl`: `114b9dfb1f7cebe41334539ff14eda1741bc7bd0f967fee760ba8c020f6d9068`
- `relevance.jsonl`: `8fec0e7f42caad36e4a1a6f2d3d078ac94bcff6e62c625cb230e3f5dc3e96a9c`

`tests/evals/test_dataset.py` validates exact schemas, stable IDs, counts,
split/owner isolation, label expectations, holdout requirements and checksums.
It also covers altered-byte rejection and split-leakage rejection.

## Label review and open questions

Manual coherence review covered all 25 episodes and all 85 label pairs. Grade
2 is direct current evidence; grade 1 is useful support; grade 0 marks the
hard/obsolete non-answer. The MBA market-density to GTM case is episode 01.

Independent human review is still required before Gate B, especially for the
transferability judgment in the ten cross-domain labels and the interpretation
of lifecycle states when a future runner applies filters. Holdout must not be
consulted for threshold/profile tuning. Corrections create a new corpus version
rather than modifying `retrieval-v0`.

**Baseline has not been measured.** S04 must consume this frozen corpus without
altering it and produce the first retrieval report.
