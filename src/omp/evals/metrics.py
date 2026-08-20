"""Pure, auditable retrieval metrics for the frozen evaluation corpus."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class QueryOutcome:
    """Sanitized outcome: identifiers only, never query or memory content."""

    query_id: str
    split: str
    kind: str
    expected_behavior: str
    returned_ids: tuple[str, ...]
    returned_metadata: tuple[Mapping[str, str], ...] = ()
    target_metadata: tuple[Mapping[str, str], ...] = ()
    deterministic_failures: tuple[str, ...] = ()


def precision_at_k(outcome: QueryOutcome, relevant_ids: set[str], k: int = 5) -> float:
    """Relevant returned results / returned results, with positive empty = zero."""
    returned = outcome.returned_ids[:k]
    return sum(item in relevant_ids for item in returned) / len(returned) if returned else 0.0


def intrusion_at_k(outcome: QueryOutcome, intrusive_ids: set[str], k: int = 5) -> float:
    """Explicitly irrelevant/hard-negative returned results / returned results."""
    returned = outcome.returned_ids[:k]
    return sum(item in intrusive_ids for item in returned) / len(returned) if returned else 0.0


def abstention_rate(outcomes: Iterable[QueryOutcome]) -> float:
    negatives = [item for item in outcomes if item.expected_behavior == "abstain"]
    return sum(not item.returned_ids for item in negatives) / len(negatives) if negatives else 0.0


def lifecycle_isolation_correctness(outcomes: Iterable[QueryOutcome]) -> float:
    # Every query has owner/state/profile checks. An empty failure list is a pass.
    all_items = list(outcomes)
    return (
        sum(not item.deterministic_failures for item in all_items) / len(all_items)
        if all_items
        else 0.0
    )


def aggregate_metrics(
    outcomes: Sequence[QueryOutcome], relevance: Mapping[str, Mapping[str, int]]
) -> dict[str, float | int]:
    positives = [item for item in outcomes if item.expected_behavior == "retrieve"]
    precisions = [
        precision_at_k(item, {mid for mid, grade in relevance[item.query_id].items() if grade > 0})
        for item in positives
    ]
    intrusions = [
        intrusion_at_k(item, {mid for mid, grade in relevance[item.query_id].items() if grade == 0})
        for item in outcomes
    ]
    deterministic_total = len(outcomes)
    deterministic_passed = sum(not item.deterministic_failures for item in outcomes)
    return {
        "queries": len(outcomes),
        "positive_queries": len(positives),
        "negative_queries": len(outcomes) - len(positives),
        "precision_at_5": sum(precisions) / len(precisions) if precisions else 0.0,
        "intrusion_at_5": sum(intrusions) / len(intrusions) if intrusions else 0.0,
        "abstention_rate": abstention_rate(outcomes),
        "lifecycle_isolation_correctness": deterministic_passed / deterministic_total
        if deterministic_total
        else 0.0,
        "deterministic_checks": deterministic_total,
        "deterministic_checks_passed": deterministic_passed,
    }


def slice_metrics(
    outcomes: Sequence[QueryOutcome], relevance: Mapping[str, Mapping[str, int]]
) -> dict[str, dict[str, dict[str, float | int]]]:
    """Publish every requested slice; a slice is never discarded for being red."""
    groups: dict[str, dict[str, list[QueryOutcome]]] = {
        "split": defaultdict(list),
        "query_kind": defaultdict(list),
        "memory_type": defaultdict(list),
        "space": defaultdict(list),
        "state": defaultdict(list),
    }
    for outcome in outcomes:
        groups["split"][outcome.split].append(outcome)
        groups["query_kind"][outcome.kind].append(outcome)
        # Target metadata prevents empty-result queries from vanishing from a
        # memory slice merely because the system failed to retrieve anything.
        for metadata in outcome.target_metadata or outcome.returned_metadata:
            for dimension in ("memory_type", "space", "state"):
                if value := metadata.get(dimension):
                    groups[dimension][value].append(outcome)
    return {
        dimension: {
            name: aggregate_metrics(items, relevance) for name, items in sorted(values.items())
        }
        for dimension, values in groups.items()
    }
