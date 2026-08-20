# Evals

`retrieval-v0` is the frozen synthetic corpus for the Alpha retrieval gate.
It is a dataset artifact, not a benchmark result: no runner, embedding tuning,
threshold tuning, database import, or baseline measurement is included here.

## Contract

- The corpus has 25 wholly synthetic episodes.  Episodes 01–20 are
  `development`; 21–25 are `holdout`.  A split is assigned per episode and
  must never be changed by selecting individual rows.
- The holdout is reserved for reporting after choices about the profile or
  threshold have been made.  It must not inform tuning.
- Stable identifiers are deliberately opaque and contain no content or real
  identity.  Provenance states that each record is synthetic.
- A change to any JSONL file creates a new dataset revision; update the
  datasheet, labels, checksums, and review record together.  Do not silently
  replace this version.

## Validate

Run the offline structural validation from the repository root:

```sh
python -c 'from pathlib import Path; from omp.evals import validate_retrieval_dataset; print(validate_retrieval_dataset(Path("evals/datasets/retrieval-v0")))'
pytest tests/evals/test_dataset.py
```

Checksums are SHA-256 of the exact UTF-8 JSONL bytes.  The validation has no
retrieval/backend dependency and is intentionally the only eval code in S03.

See the [datasheet](datasets/retrieval-v0/datasheet.md) for design and label
limits, and the [rubric](rubrics/retrieval-v0.md) for relevance adjudication.
