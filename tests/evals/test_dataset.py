from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from omp.evals import DatasetValidationError, validate_retrieval_dataset

DATASET_DIR = Path(__file__).resolve().parents[2] / "evals" / "datasets" / "retrieval-v0"


def test_retrieval_v0_is_structurally_frozen_and_complete() -> None:
    summary = validate_retrieval_dataset(DATASET_DIR)

    assert summary.memories == 125
    assert summary.queries == 50
    assert summary.relevance_pairs == 85
    assert summary.episodes_by_split == {"development": 20, "holdout": 5}
    assert summary.queries_by_split == {"development": 40, "holdout": 10}
    assert summary.query_behavior_counts == {"retrieve": 35, "abstain": 15}
    assert summary.cross_domain_queries == 10


def test_retrieval_v0_rejects_modified_bytes_without_new_checksum(tmp_path: Path) -> None:
    copied = tmp_path / "retrieval-v0"
    shutil.copytree(DATASET_DIR, copied)
    queries = copied / "queries.jsonl"
    changed = queries.read_text(encoding="utf-8").replace("mba density", "altered density", 1)
    queries.write_text(changed, encoding="utf-8")

    with pytest.raises(DatasetValidationError, match="checksum mismatch"):
        validate_retrieval_dataset(copied)


def test_retrieval_v0_rejects_episode_split_leakage_even_with_matching_checksum(
    tmp_path: Path,
) -> None:
    copied = tmp_path / "retrieval-v0"
    shutil.copytree(DATASET_DIR, copied)
    memories = copied / "memories.jsonl"
    text = memories.read_text(encoding="utf-8").replace(
        '"split":"development"', '"split":"holdout"', 1
    )
    memories.write_text(text, encoding="utf-8")

    with pytest.raises(DatasetValidationError, match="crosses splits"):
        validate_retrieval_dataset(copied)
