from omp.evals.metrics import (
    QueryOutcome,
    abstention_rate,
    aggregate_metrics,
    intrusion_at_k,
    precision_at_k,
)


def test_manual_precision_intrusion_and_abstention_examples() -> None:
    positive = QueryOutcome("q1", "development", "positive", "retrieve", ("m1", "m2", "m3"))
    negative_empty = QueryOutcome("q2", "development", "negative", "abstain", ())
    negative_returned = QueryOutcome("q3", "holdout", "hard_negative", "abstain", ("m4",))
    relevance = {"q1": {"m1": 2, "m2": 0, "m3": 1}, "q2": {}, "q3": {"m4": 0}}

    assert precision_at_k(positive, {"m1", "m3"}) == 2 / 3
    assert intrusion_at_k(positive, {"m2"}) == 1 / 3
    assert abstention_rate([negative_empty, negative_returned]) == 0.5
    measured = aggregate_metrics([positive, negative_empty, negative_returned], relevance)
    assert measured["precision_at_5"] == 2 / 3
    assert measured["intrusion_at_5"] == (1 / 3 + 0 + 1) / 3
    assert measured["abstention_rate"] == 0.5


def test_positive_empty_result_is_zero_and_deterministic_failure_is_counted() -> None:
    outcome = QueryOutcome(
        "q1", "development", "positive", "retrieve", (), deterministic_failures=("owner",)
    )
    metrics = aggregate_metrics([outcome], {"q1": {"m1": 2}})

    assert metrics["precision_at_5"] == 0.0
    assert metrics["lifecycle_isolation_correctness"] == 0.0
