from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("torch")
pytest.importorskip("transformers")

from omp.evals.metrics import QueryOutcome
from omp.evals.semantic_harness import _failure_ids, cosine, load_candidate, outcome_at_threshold

ROOT = Path(__file__).resolve().parents[2]


def test_cosine_uses_normalized_vectors() -> None:
    assert cosine((1.0, 0.0), (0.5, 0.5)) == 0.5


def test_failure_artifact_uses_only_identifiers() -> None:
    outcome = QueryOutcome(
        "query-01-a", "development", "positive", "retrieve", ("memory-01-current",)
    )
    failures = _failure_ids([outcome], {"query-01-a": {"memory-01-core": 2}})

    assert failures == [
        {
            "query_id": "query-01-a",
            "failures": ["no_relevant_result"],
            "returned_memory_ids": ["memory-01-current"],
        }
    ]


def test_semantic_configs_are_versioned_and_development_threshold_is_frozen() -> None:
    candidate = load_candidate(
        ROOT / "evals/configs/semantic-all-minilm-l6-v2.yaml",
        Path("/private/tmp"),
    )

    assert candidate.dimension == 384
    assert candidate.threshold == 0.78
    assert candidate.model_license == "Apache-2.0"
    assert candidate.passage_prefix == "__none__"

    e5 = load_candidate(
        ROOT / "evals/configs/semantic-e5-small-v2.yaml",
        Path("/private/tmp"),
    )
    # ADR 0008 freezes the provider boundary with a trailing separator space.
    assert e5.query_prefix == "query: "
    assert e5.passage_prefix == "passage: "

    bge = load_candidate(
        ROOT / "evals/configs/semantic-bge-small-en-v1.5.yaml",
        Path("/private/tmp"),
    )
    assert bge.pooling == "cls"
    assert bge.query_prefix == "Represent this sentence for searching relevant passages: "
    assert bge.passage_prefix == "__none__"


def test_e5_promotion_configuration_is_frozen_by_adr_0008() -> None:
    promotion = load_candidate(
        ROOT / "evals/configs/semantic-e5-small-v2-promotion.yaml",
        Path("/private/tmp"),
    )

    assert promotion.model_id == "intfloat/e5-small-v2"
    assert promotion.model_revision == "ffb93f3bd4047442299a41ebb6fa998a38507c52"
    assert promotion.profile_version == "e5-small-v2-s09"
    assert promotion.pooling == "mean"
    assert promotion.query_prefix == "query: "
    assert promotion.passage_prefix == "passage: "
    assert promotion.dimension == 384
    assert promotion.threshold == 0.76
    assert promotion.candidate_limit == 50
    assert promotion.result_limit == 5


def test_thresholded_harness_result_uses_gateway_score_tie_break() -> None:
    candidate = load_candidate(
        ROOT / "evals/configs/semantic-e5-small-v2.yaml",
        Path("/private/tmp"),
    )
    query = {
        "query_id": "query-01-a",
        "owner_id": "owner-a",
        "kind": "positive",
        "expected_behavior": "retrieve",
        "filters": {"state": "active"},
    }
    ranked = [
        (
            0.81,
            {
                "memory_id": "m-low",
                "owner_id": "owner-a",
                "state": "active",
                "importance": 0.0,
                "confidence": 0.0,
                "type": "fact",
                "space": "default",
            },
        ),
        (
            0.80,
            {
                "memory_id": "m-high",
                "owner_id": "owner-a",
                "state": "active",
                "importance": 1.0,
                "confidence": 1.0,
                "type": "fact",
                "space": "default",
            },
        ),
    ]

    outcome = outcome_at_threshold(
        query=query,
        ranked=ranked,
        candidate=candidate,
        threshold=0.78,
    )

    assert outcome.returned_ids == ("m-high", "m-low")
