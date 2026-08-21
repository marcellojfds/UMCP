"""Development-only local semantic-embedding comparison harness.

This module is deliberately offline and does not implement the production
``EmbeddingProvider`` port.  It exists only to choose a candidate before S09.
The harness validates the frozen corpus, then reads and evaluates *only* its
development split.  It uses the existing metrics and reports IDs only.
"""

from __future__ import annotations

import argparse
import json
import math
import platform
import re
import time
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import torch
from transformers import AutoModel, AutoTokenizer  # type: ignore[import-untyped]

from omp import __version__

from .dataset import validate_retrieval_dataset
from .metrics import QueryOutcome, aggregate_metrics, slice_metrics
from .runner import _decision, _git_metadata, _percentile, _sha256, load_config


@dataclass(frozen=True, slots=True)
class SemanticCandidate:
    """Versioned local-model metadata supplied by an experimental config."""

    config_path: Path
    model_root: Path
    model_id: str
    model_revision: str
    model_license: str
    profile_id: str
    profile_version: str
    dimension: int
    threshold: float
    candidate_limit: int
    result_limit: int
    warmups: int
    runs: int
    p95_budget_ms: int
    query_prefix: str
    passage_prefix: str
    pooling: str
    max_length: int


def _jsonl(path: Path) -> Iterable[dict[str, Any]]:
    for line in path.read_text(encoding="utf-8").splitlines():
        yield json.loads(line)


def load_candidate(config_path: Path, model_root: Path) -> SemanticCandidate:
    """Load one flat config without accepting implicit model downloads."""
    config = load_config(config_path)
    required = {
        "model_id",
        "model_revision",
        "model_license",
        "query_prefix",
        "passage_prefix",
        "max_length",
    }
    missing = required - set(config)
    if missing:
        raise ValueError(f"semantic eval config missing: {', '.join(sorted(missing))}")
    if int(config["dimension"]) > 384:
        raise ValueError("semantic eval dimension must not exceed 384")
    if not model_root.is_dir():
        raise ValueError(f"local model directory is missing: {model_root}")
    return SemanticCandidate(
        config_path=config_path,
        model_root=model_root,
        model_id=str(config["model_id"]),
        model_revision=str(config["model_revision"]),
        model_license=str(config["model_license"]),
        profile_id=str(config["profile_id"]),
        profile_version=str(config["profile_version"]),
        dimension=int(config["dimension"]),
        threshold=float(config["threshold"]),
        candidate_limit=int(config["candidate_limit"]),
        result_limit=int(config["result_limit"]),
        warmups=int(config["warmups"]),
        runs=int(config["runs"]),
        p95_budget_ms=int(config["p95_budget_ms"]),
        query_prefix=str(config["query_prefix"]),
        passage_prefix=str(config["passage_prefix"]),
        pooling=str(config.get("pooling", "mean")),
        max_length=int(config["max_length"]),
    )


class LocalEncoder:
    """Transformer encoder used only by this experimental harness."""

    def __init__(self, candidate: SemanticCandidate) -> None:
        self._candidate = candidate
        self._tokenizer = AutoTokenizer.from_pretrained(candidate.model_root, local_files_only=True)
        self._model = AutoModel.from_pretrained(candidate.model_root, local_files_only=True)
        self._model.eval()
        hidden_size = int(self._model.config.hidden_size)
        if hidden_size != candidate.dimension:
            raise ValueError(
                f"model dimension {hidden_size} differs from config {candidate.dimension}"
            )

    def encode(self, text: str, *, query: bool = False) -> tuple[float, ...]:
        configured_prefix = (
            self._candidate.query_prefix if query else self._candidate.passage_prefix
        )
        prefix = "" if configured_prefix == "__none__" else configured_prefix
        prepared = f"{prefix}{text}"
        encoded = self._tokenizer(
            prepared,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=self._candidate.max_length,
        )
        with torch.inference_mode():
            output = self._model(**encoded).last_hidden_state
        if self._candidate.pooling == "cls":
            pooled = output[:, 0, :]
        elif self._candidate.pooling == "mean":
            mask = encoded["attention_mask"].unsqueeze(-1).to(output.dtype)
            pooled = (output * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1)
        else:
            raise ValueError(f"unsupported semantic pooling: {self._candidate.pooling}")
        normalized = torch.nn.functional.normalize(pooled, p=2, dim=1)[0]
        return tuple(float(value) for value in normalized.tolist())


def cosine(left: Sequence[float], right: Sequence[float]) -> float:
    """Cosine for normalized vectors, kept dependency-free and testable."""
    return sum(a * b for a, b in zip(left, right, strict=True))


def _metadata(memory: Mapping[str, Any]) -> dict[str, str]:
    return {
        "memory_type": str(memory["type"]),
        "space": str(memory["space"]),
        "state": str(memory["state"]),
    }


def rank_before_threshold(
    *,
    query: Mapping[str, Any],
    records: Sequence[Mapping[str, Any]],
    vectors: Mapping[str, Sequence[float]],
    encoder: LocalEncoder,
    candidate: SemanticCandidate,
) -> tuple[list[tuple[float, Mapping[str, Any]]], float]:
    """Apply the documented owner/state/space/type filters before ranking."""
    start = time.perf_counter_ns()
    query_vector = encoder.encode(str(query["query"]), query=True)
    filters = query["filters"]
    expected_state = filters.get("state", "active")
    eligible = [
        memory
        for memory in records
        if memory["owner_id"] == query["owner_id"]
        and memory["state"] == expected_state
        and (not filters.get("space") or memory["space"] == filters["space"])
        and (not filters.get("type") or memory["type"] == filters["type"])
    ]
    ranked = sorted(
        ((cosine(query_vector, vectors[str(memory["memory_id"])]), memory) for memory in eligible),
        key=lambda item: (-item[0], str(item[1]["memory_id"])),
    )[: candidate.candidate_limit]
    return ranked, (time.perf_counter_ns() - start) / 1_000_000


def outcome_at_threshold(
    *,
    query: Mapping[str, Any],
    ranked: Sequence[tuple[float, Mapping[str, Any]]],
    candidate: SemanticCandidate,
    threshold: float,
) -> QueryOutcome:
    """Apply serving abstention after the complete eligible ranking is fixed."""
    # Calibration callers supply a fold-selected threshold without mutating the
    # candidate config. The configured value is used by ``retrieve`` above.
    returned = [
        (max(0.0, min(1.0, similarity)), memory)
        for similarity, memory in ranked
        if max(0.0, min(1.0, similarity)) >= threshold
    ]
    # This is intentionally the same post-threshold score and tie-break used
    # by MemoryApplicationService.search. Candidate generation remains cosine
    # ordered; the public result order incorporates fixture importance and
    # confidence after abstention, exactly as the gateway does.
    returned.sort(
        key=lambda item: (
            -_serving_score(item[0], item[1]),
            -item[0],
            str(item[1]["memory_id"]),
        )
    )
    returned = returned[: candidate.result_limit]
    filters = query["filters"]
    expected_state = filters.get("state", "active")
    failures: set[str] = set()
    for _, memory in returned:
        if memory["owner_id"] != query["owner_id"]:
            failures.add("owner")
        if memory["state"] != expected_state:
            failures.add("state")
        if filters.get("space") and memory["space"] != filters["space"]:
            failures.add("space")
        if filters.get("type") and memory["type"] != filters["type"]:
            failures.add("type")
    return QueryOutcome(
        query_id=str(query["query_id"]),
        split="development",
        kind=str(query["kind"]),
        expected_behavior=str(query["expected_behavior"]),
        returned_ids=tuple(str(memory["memory_id"]) for _, memory in returned),
        returned_metadata=tuple(
            {
                **_metadata(memory),
                "score": f"{_serving_score(similarity, memory):.6f}",
            }
            for similarity, memory in returned
        ),
        deterministic_failures=tuple(sorted(failures)),
    )


def _serving_score(similarity: float, memory: Mapping[str, Any]) -> float:
    return (
        (0.75 * similarity)
        + (0.15 * float(memory["importance"]))
        + (0.10 * float(memory["confidence"]))
    )


def retrieve(
    *,
    query: Mapping[str, Any],
    records: Sequence[Mapping[str, Any]],
    vectors: Mapping[str, Sequence[float]],
    encoder: LocalEncoder,
    candidate: SemanticCandidate,
) -> tuple[QueryOutcome, float]:
    """Retrieve with the historical configured threshold for baseline evidence."""
    ranked, elapsed = rank_before_threshold(
        query=query, records=records, vectors=vectors, encoder=encoder, candidate=candidate
    )
    return (
        outcome_at_threshold(
            query=query, ranked=ranked, candidate=candidate, threshold=candidate.threshold
        ),
        elapsed,
    )


def _development_data(
    dataset_dir: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, dict[str, int]]]:
    """Validate frozen data, then materialize development records only."""
    validate_retrieval_dataset(dataset_dir)
    memories = [
        record
        for record in _jsonl(dataset_dir / "memories.jsonl")
        if record["split"] == "development"
    ]
    queries = [
        record
        for record in _jsonl(dataset_dir / "queries.jsonl")
        if record["split"] == "development"
    ]
    relevance: dict[str, dict[str, int]] = defaultdict(dict)
    for label in _jsonl(dataset_dir / "relevance.jsonl"):
        if label["query_id"] in {query["query_id"] for query in queries}:
            relevance[str(label["query_id"])][str(label["memory_id"])] = int(label["grade"])
    return memories, queries, relevance


def _failure_ids(
    outcomes: Sequence[QueryOutcome], relevance: Mapping[str, Mapping[str, int]]
) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    for outcome in outcomes:
        codes = list(outcome.deterministic_failures)
        relevant = {
            memory_id for memory_id, grade in relevance[outcome.query_id].items() if grade > 0
        }
        intrusive = {
            memory_id for memory_id, grade in relevance[outcome.query_id].items() if grade == 0
        }
        if outcome.expected_behavior == "retrieve" and not outcome.returned_ids:
            codes.append("no_retrieval")
        elif outcome.expected_behavior == "retrieve" and not set(outcome.returned_ids) & relevant:
            codes.append("no_relevant_result")
        if set(outcome.returned_ids) & intrusive:
            codes.append("intrusion")
        if outcome.expected_behavior == "abstain" and outcome.returned_ids:
            codes.append("abstention_failure")
        if codes:
            failures.append(
                {
                    "query_id": outcome.query_id,
                    "failures": sorted(set(codes)),
                    "returned_memory_ids": list(outcome.returned_ids),
                }
            )
    return failures


def _served_results(outcomes: Sequence[QueryOutcome]) -> list[dict[str, Any]]:
    """Identifier/score-only trace for harness/PostgreSQL equivalence."""
    return [
        {
            "query_id": outcome.query_id,
            "returned": [
                {"memory_id": memory_id, "score": float(metadata["score"])}
                for memory_id, metadata in zip(
                    outcome.returned_ids,
                    outcome.returned_metadata,
                    strict=True,
                )
            ],
        }
        for outcome in sorted(outcomes, key=lambda item: item.query_id)
    ]


def _with_target_metadata(
    outcomes: Sequence[QueryOutcome],
    relevance: Mapping[str, Mapping[str, int]],
    memory_by_id: Mapping[str, Mapping[str, Any]],
) -> list[QueryOutcome]:
    return [
        replace(
            outcome,
            target_metadata=tuple(
                _metadata(memory_by_id[memory_id])
                for memory_id, grade in relevance[outcome.query_id].items()
                if grade > 0
            ),
        )
        for outcome in outcomes
    ]


def _ranking_metrics(
    *,
    queries: Sequence[Mapping[str, Any]],
    rankings: Mapping[str, Sequence[tuple[float, Mapping[str, Any]]]],
    relevance: Mapping[str, Mapping[str, int]],
) -> dict[str, float]:
    """Threshold-independent ranking diagnostics for development only."""
    positives = [query for query in queries if query["expected_behavior"] == "retrieve"]
    recalls: dict[int, list[float]] = {1: [], 5: [], 10: [], 50: []}
    mrr: list[float] = []
    ndcg: list[float] = []
    coverage: list[float] = []
    relevant_scores: list[float] = []
    negative_scores: list[float] = []
    for query in positives:
        query_id = str(query["query_id"])
        grades = relevance[query_id]
        relevant = {memory_id for memory_id, grade in grades.items() if grade > 0}
        ranked = rankings[query_id]
        returned_ids = [str(memory["memory_id"]) for _, memory in ranked]
        for k in recalls:
            recalls[k].append(
                len(set(returned_ids[:k]) & relevant) / len(relevant) if relevant else 0.0
            )
        first_rank = next(
            (index + 1 for index, value in enumerate(returned_ids) if value in relevant),
            None,
        )
        mrr.append(1 / first_rank if first_rank else 0.0)
        dcg = sum(
            (2 ** grades.get(memory_id, 0) - 1) / math.log2(index + 2)
            for index, memory_id in enumerate(returned_ids[:5])
        )
        ideal = sorted((grade for grade in grades.values() if grade > 0), reverse=True)
        idcg = sum((2**grade - 1) / math.log2(index + 2) for index, grade in enumerate(ideal[:5]))
        ndcg.append(dcg / idcg if idcg else 0.0)
        coverage.append(float(bool(set(returned_ids) & relevant)))
        for score, memory in ranked:
            grade = grades.get(str(memory["memory_id"]))
            if grade is None:
                continue
            if grade > 0:
                relevant_scores.append(score)
            else:
                negative_scores.append(score)
    negative_best = [
        rankings[str(query["query_id"])][0][0]
        for query in queries
        if query["expected_behavior"] == "abstain" and rankings[str(query["query_id"])]
    ]
    recall_result = {
        f"recall_at_{k}": round(sum(values) / len(values), 6) if values else 0.0
        for k, values in recalls.items()
    }
    result = {
        **recall_result,
        "mrr": round(sum(mrr) / len(mrr), 6) if mrr else 0.0,
        "ndcg_at_5": round(sum(ndcg) / len(ndcg), 6) if ndcg else 0.0,
        "positive_candidate_coverage": (
            round(sum(coverage) / len(coverage), 6) if coverage else 0.0
        ),
        "mean_relevant_score": (
            round(sum(relevant_scores) / len(relevant_scores), 6) if relevant_scores else 0.0
        ),
        "mean_labeled_negative_score": (
            round(sum(negative_scores) / len(negative_scores), 6) if negative_scores else 0.0
        ),
        "mean_negative_query_best_score": (
            round(sum(negative_best) / len(negative_best), 6) if negative_best else 0.0
        ),
    }
    result["mean_relevant_minus_labeled_negative"] = round(
        result["mean_relevant_score"] - result["mean_labeled_negative_score"], 6
    )
    return result


def _diagnostic_artifact(
    *,
    queries: Sequence[Mapping[str, Any]],
    rankings: Mapping[str, Sequence[tuple[float, Mapping[str, Any]]]],
    relevance: Mapping[str, Mapping[str, int]],
) -> dict[str, Any]:
    """IDs and scores only; text fields must never enter an eval artifact."""
    per_query: list[dict[str, Any]] = []
    for query in queries:
        query_id = str(query["query_id"])
        grades = relevance[query_id]
        ranked = rankings[query_id]
        first_relevant_rank = next(
            (
                index + 1
                for index, (_, memory) in enumerate(ranked)
                if grades.get(str(memory["memory_id"]), 0) > 0
            ),
            None,
        )
        per_query.append(
            {
                "query_id": query_id,
                "filters_applied": {
                    "owner": True,
                    "state": True,
                    "space": bool(query["filters"].get("space")),
                    "type": bool(query["filters"].get("type")),
                },
                "top_50_before_threshold": [
                    {"memory_id": str(memory["memory_id"]), "score": round(score, 8)}
                    for score, memory in ranked[:50]
                ],
                "first_relevant_rank": first_relevant_rank,
                "relevant_scores": sorted(
                    round(score, 8)
                    for score, memory in ranked
                    if grades.get(str(memory["memory_id"]), 0) > 0
                ),
                "labeled_negative_scores": sorted(
                    round(score, 8)
                    for score, memory in ranked
                    if grades.get(str(memory["memory_id"]), 0) == 0
                ),
                "best_score_if_abstention_query": (
                    round(ranked[0][0], 8)
                    if query["expected_behavior"] == "abstain" and ranked
                    else None
                ),
            }
        )
    return {
        "ranking_metrics": _ranking_metrics(
            queries=queries,
            rankings=rankings,
            relevance=relevance,
        ),
        "queries": per_query,
    }


def _episode_fold(query: Mapping[str, Any]) -> int:
    match = re.fullmatch(r"episode-(\d+)", str(query["episode_id"]))
    if match is None:
        raise ValueError("development episode IDs must be numbered deterministically")
    return (int(match.group(1)) - 1) % 5


def _slice_floor_passes(slices: Mapping[str, Any]) -> bool:
    return all(
        value["positive_queries"] < 5 or value["precision_at_5"] >= 0.60
        for value in slices["query_kind"].values()
    )


def _calibration_artifact(
    *,
    candidate: SemanticCandidate,
    queries: Sequence[Mapping[str, Any]],
    rankings: Mapping[str, Sequence[tuple[float, Mapping[str, Any]]]],
    relevance: Mapping[str, Mapping[str, int]],
    memory_by_id: Mapping[str, Mapping[str, Any]],
    p95: float,
) -> dict[str, Any]:
    """Five-fold, episode-grouped calibration whose validation is never selected on."""
    thresholds = tuple(round(0.50 + 0.01 * item, 2) for item in range(41))
    folds: list[dict[str, Any]] = []
    oof: list[QueryOutcome] = []
    for fold in range(5):
        calibration_queries = [query for query in queries if _episode_fold(query) != fold]
        validation_queries = [query for query in queries if _episode_fold(query) == fold]
        eligible: list[tuple[float, dict[str, float | int], dict[str, Any]]] = []
        for threshold in thresholds:
            outcomes = _with_target_metadata(
                [
                    outcome_at_threshold(
                        query=query,
                        ranked=rankings[str(query["query_id"])],
                        candidate=candidate,
                        threshold=threshold,
                    )
                    for query in calibration_queries
                ],
                relevance,
                memory_by_id,
            )
            calibration_metrics = aggregate_metrics(outcomes, relevance)
            calibration_slices = slice_metrics(outcomes, relevance)
            if (
                calibration_metrics["abstention_rate"] >= 0.90
                and calibration_metrics["intrusion_at_5"] <= 0.10
                and calibration_metrics["lifecycle_isolation_correctness"] == 1.0
                and _slice_floor_passes(calibration_slices)
            ):
                eligible.append((threshold, calibration_metrics, calibration_slices))
        if not eligible:
            folds.append(
                {
                    "fold": fold,
                    "calibration_episode_count": 16,
                    "validation_episode_count": 4,
                    "selected_threshold": None,
                    "selection": "no threshold satisfies preregistered calibration constraints",
                }
            )
            continue
        selected_threshold, selected_metrics, _ = max(
            eligible, key=lambda item: (item[1]["precision_at_5"], item[0])
        )
        validation_outcomes = _with_target_metadata(
            [
                outcome_at_threshold(
                    query=query,
                    ranked=rankings[str(query["query_id"])],
                    candidate=candidate,
                    threshold=selected_threshold,
                )
                for query in validation_queries
            ],
            relevance,
            memory_by_id,
        )
        oof.extend(validation_outcomes)
        folds.append(
            {
                "fold": fold,
                "calibration_episode_count": 16,
                "validation_episode_count": 4,
                "selected_threshold": selected_threshold,
                "calibration_metrics": selected_metrics,
                "validation_metrics": aggregate_metrics(validation_outcomes, relevance),
            }
        )
    complete = len(oof) == len(queries)
    oof_metrics = aggregate_metrics(oof, relevance) if complete else None
    oof_slices = slice_metrics(oof, relevance) if complete else None
    decision, reasons = (
        _decision(oof_metrics, oof_slices, p95, {"p95_budget_ms": candidate.p95_budget_ms})
        if complete and oof_metrics is not None and oof_slices is not None
        else ("NO-GO", ["one or more calibration folds had no eligible threshold"])
    )
    return {
        "protocol": {
            "folds": 5,
            "unit": "episode",
            "threshold_grid": list(thresholds),
            "selection": (
                "abstention, intrusion, lifecycle/isolation and slice floor; "
                "then max precision@5; then higher threshold"
            ),
        },
        "folds": folds,
        "out_of_fold_metrics": oof_metrics,
        "out_of_fold_slices": oof_slices,
        "decision": decision,
        "reasons": reasons,
    }


def _assert_local_revision(candidate: SemanticCandidate) -> None:
    """Refuse a downloaded snapshot whose recorded revision differs from config."""
    metadata = candidate.model_root / ".cache/huggingface/download/model.safetensors.metadata"
    revision_file = candidate.model_root / "REVISION"
    if metadata.is_file():
        revision = metadata.read_text(encoding="utf-8").splitlines()[0]
    elif revision_file.is_file():
        revision = revision_file.read_text(encoding="utf-8").splitlines()[0]
    else:
        raise ValueError(f"missing local model revision metadata: {metadata} or {revision_file}")
    if revision != candidate.model_revision:
        raise ValueError(
            f"downloaded revision {revision} differs from configured {candidate.model_revision}"
        )


def evaluate_candidate(candidate: SemanticCandidate, dataset_dir: Path) -> dict[str, Any]:
    """Evaluate one local candidate on development without touching the holdout."""
    records, queries, relevance = _development_data(dataset_dir)
    _assert_local_revision(candidate)
    encoder = LocalEncoder(candidate)
    vectors = {
        str(record["memory_id"]): encoder.encode(str(record["content"])) for record in records
    }
    for _ in range(candidate.warmups):
        for query in queries:
            retrieve(
                query=query, records=records, vectors=vectors, encoder=encoder, candidate=candidate
            )
    measured: dict[str, QueryOutcome] = {}
    timings: list[float] = []
    for _ in range(candidate.runs):
        for query in queries:
            outcome, elapsed = retrieve(
                query=query, records=records, vectors=vectors, encoder=encoder, candidate=candidate
            )
            previous = measured.get(outcome.query_id)
            if previous is not None and previous.returned_ids != outcome.returned_ids:
                outcome = replace(outcome, deterministic_failures=("nondeterministic",))
            measured[outcome.query_id] = outcome
            timings.append(elapsed)
    memory_by_id = {str(record["memory_id"]): record for record in records}
    outcomes = _with_target_metadata(list(measured.values()), relevance, memory_by_id)
    rankings = {
        str(query["query_id"]): rank_before_threshold(
            query=query,
            records=records,
            vectors=vectors,
            encoder=encoder,
            candidate=candidate,
        )[0]
        for query in queries
    }
    metrics = aggregate_metrics(outcomes, relevance)
    slices = slice_metrics(outcomes, relevance)
    p50, p95 = _percentile(timings, 0.50), _percentile(timings, 0.95)
    decision, reasons = _decision(
        metrics,
        slices,
        p95,
        {"p95_budget_ms": candidate.p95_budget_ms},
    )
    files = [
        path
        for path in candidate.model_root.rglob("*")
        if path.is_file() and "/.cache/" not in str(path)
    ]
    weight_path = candidate.model_root / "model.safetensors"
    return {
        "candidate": {
            "model_id": candidate.model_id,
            "model_revision": candidate.model_revision,
            "license": candidate.model_license,
            "profile_id": candidate.profile_id,
            "profile_version": candidate.profile_version,
            "dimension": candidate.dimension,
            "metric": "cosine",
            "query_prefix": candidate.query_prefix,
            "passage_prefix": candidate.passage_prefix,
            "pooling": candidate.pooling,
            "max_length": candidate.max_length,
            "model_size_bytes": weight_path.stat().st_size,
            "model_files_sha256": {
                str(path.relative_to(candidate.model_root)): _sha256(path) for path in sorted(files)
            },
        },
        "config": {
            **load_config(candidate.config_path),
            "sha256": _sha256(candidate.config_path),
        },
        "development_only": True,
        "runs": {
            "warmups": candidate.warmups,
            "runs": candidate.runs,
            "measured_searches": len(timings),
        },
        "metrics": metrics,
        "slices": slices,
        "latency_ms": {"p50": p50, "p95": p95, "budget_ms": candidate.p95_budget_ms},
        "external_cost": {
            "currency": "USD",
            "amount": 0.0,
            "reason": "local model inference; no API calls",
        },
        "decision": decision,
        "reasons": reasons,
        "failures": _failure_ids(outcomes, relevance),
        "served_results": _served_results(outcomes),
        "diagnostic": _diagnostic_artifact(
            queries=queries,
            rankings=rankings,
            relevance=relevance,
        ),
        "calibration": _calibration_artifact(
            candidate=candidate,
            queries=queries,
            rankings=rankings,
            relevance=relevance,
            memory_by_id=memory_by_id,
            p95=p95,
        ),
    }


def _markdown(report: Mapping[str, Any]) -> str:
    rows = [
        "# S08 semantic embedding comparison",
        "",
        f"Decision: **{report['decision']}**",
        "",
        "Only `development` was evaluated. The holdout was not executed.",
        "",
        "| Candidate | precision@5 | intrusion@5 | abstention | lifecycle/isolation | "
        "p50 / p95 (ms) | Result |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for item in report["candidates"]:
        metrics, latency, candidate = item["metrics"], item["latency_ms"], item["candidate"]
        rows.append(
            f"| {candidate['model_id']} | {metrics['precision_at_5']:.3f} | "
            f"{metrics['intrusion_at_5']:.3f} | {metrics['abstention_rate']:.3f} | "
            f"{metrics['lifecycle_isolation_correctness']:.3f} | {latency['p50']:.3f} / "
            f"{latency['p95']:.3f} | {item['decision']} |"
        )
    rows.extend(
        ["", "## Decision reasons", "", *(f"- {reason}" for reason in report["reasons"]), ""]
    )
    return "\n".join(rows)


def run_comparison(
    *, candidates: Sequence[SemanticCandidate], dataset_dir: Path, output_root: Path
) -> Path:
    """Produce one immutable development artifact for one or two candidates."""
    if not 1 <= len(candidates) <= 2:
        raise ValueError("semantic development accepts one or two candidates")
    results = [evaluate_candidate(candidate, dataset_dir) for candidate in candidates]
    passing = [item for item in results if item["decision"] == "GO"]
    selected = passing[0]["candidate"]["model_id"] if len(passing) == 1 else None
    reasons = (
        [f"selected {selected}: sole candidate satisfying every development gate"]
        if selected
        else [
            "NO-GO: zero or multiple candidates satisfy the development gates; "
            "no selection is valid"
        ]
    )
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    revision = _git_metadata(Path.cwd())["revision"][:12]
    destination = output_root / f"{stamp}-{revision}-semantic-development"
    destination.mkdir(parents=True, exist_ok=False)
    report: dict[str, Any] = {
        "schema_version": 1,
        "session": str(load_config(candidates[0].config_path).get("session", "S08")),
        "decision": "GO-CANDIDATE" if selected else "NO-GO",
        "selected_candidate": selected,
        "reasons": reasons,
        "holdout_executed": False,
        "git": _git_metadata(Path.cwd()),
        "dataset": {
            "name": dataset_dir.name,
            "sha256": {
                name: _sha256(dataset_dir / name)
                for name in ("memories.jsonl", "queries.jsonl", "relevance.jsonl", "checksums.json")
            },
        },
        "environment": {
            "python": platform.python_version(),
            "omp": __version__,
            "torch": torch.__version__,
            "transformers": __import__("transformers").__version__,
            "platform": platform.platform(),
            "device": "cpu",
            "backend": "experimental-in-memory-local",
        },
        "candidates": results,
    }
    (destination / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (destination / "report.md").write_text(_markdown(report), encoding="utf-8")
    (destination / "checksums.json").write_text(
        json.dumps(
            {name: _sha256(destination / name) for name in ("report.json", "report.md")},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return destination


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", action="append", required=True, type=Path)
    parser.add_argument("--model-root", action="append", required=True, type=Path)
    parser.add_argument("--dataset", default=Path("evals/datasets/retrieval-v0"), type=Path)
    parser.add_argument("--output-root", default=Path("evals/reports"), type=Path)
    args = parser.parse_args()
    if len(args.config) != len(args.model_root):
        raise SystemExit("--config and --model-root must have matching counts")
    candidates = [
        load_candidate(config, root)
        for config, root in zip(args.config, args.model_root, strict=True)
    ]
    print(
        run_comparison(
            candidates=candidates, dataset_dir=args.dataset, output_root=args.output_root
        )
    )


if __name__ == "__main__":
    main()
