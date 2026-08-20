"""Strict offline validation for frozen retrieval evaluation datasets.

This module intentionally has no dependency on retrieval, embeddings, storage,
or production application services.  It only validates dataset structure.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from omp.domain import MemoryState, MemoryType, SourceType


class DatasetValidationError(ValueError):
    """Raised when a frozen evaluation dataset violates its contract."""


@dataclass(frozen=True, slots=True)
class DatasetValidationSummary:
    """Counts produced after a dataset passes all structural checks."""

    memories: int
    queries: int
    relevance_pairs: int
    episodes_by_split: Mapping[str, int]
    queries_by_split: Mapping[str, int]
    query_behavior_counts: Mapping[str, int]
    cross_domain_queries: int


_ID = re.compile(r"^[a-z][a-z0-9-]{2,63}$")
_SPLITS = {"development", "holdout"}
_BEHAVIORS = {"retrieve", "abstain"}
_KINDS = {"positive", "negative", "cross_domain", "hard_negative"}
_MEMORY_FIELDS = {
    "memory_id",
    "episode_id",
    "split",
    "owner_id",
    "space",
    "type",
    "state",
    "content",
    "importance",
    "confidence",
    "provenance",
}
_QUERY_FIELDS = {
    "query_id",
    "episode_id",
    "split",
    "owner_id",
    "query",
    "filters",
    "kind",
    "expected_behavior",
}
_RELEVANCE_FIELDS = {"query_id", "memory_id", "grade", "reason"}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise DatasetValidationError(f"cannot read {path}") from exc
    if not lines:
        raise DatasetValidationError(f"{path.name} must not be empty")
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(lines, start=1):
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise DatasetValidationError(f"{path.name}:{line_number} is not valid JSON") from exc
        if not isinstance(record, dict):
            raise DatasetValidationError(f"{path.name}:{line_number} must be an object")
        records.append(record)
    return records


def _require_exact_fields(record: Mapping[str, Any], fields: set[str], label: str) -> None:
    if set(record) != fields:
        raise DatasetValidationError(f"{label} has unexpected or missing fields")


def _require_id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise DatasetValidationError(f"{label} must be a stable lowercase identifier")
    return value


def _require_unit_interval(value: Any, label: str) -> None:
    if not isinstance(value, int | float) or isinstance(value, bool) or not 0 <= value <= 1:
        raise DatasetValidationError(f"{label} must be a number in [0, 1]")


def _unique(records: Iterable[Mapping[str, Any]], key: str, label: str) -> set[str]:
    values = [_require_id(record[key], f"{label}.{key}") for record in records]
    if len(values) != len(set(values)):
        raise DatasetValidationError(f"duplicate {label} {key}")
    return set(values)


def _validate_memory(record: Mapping[str, Any]) -> None:
    _require_exact_fields(record, _MEMORY_FIELDS, "memory")
    _require_id(record["memory_id"], "memory.memory_id")
    _require_id(record["episode_id"], "memory.episode_id")
    _require_id(record["owner_id"], "memory.owner_id")
    if record["split"] not in _SPLITS:
        raise DatasetValidationError("memory.split is invalid")
    if record["type"] not in {item.value for item in MemoryType}:
        raise DatasetValidationError("memory.type is invalid")
    if record["state"] not in {item.value for item in MemoryState}:
        raise DatasetValidationError("memory.state is invalid")
    if not isinstance(record["space"], str) or not record["space"].strip():
        raise DatasetValidationError("memory.space must be non-empty")
    if not isinstance(record["content"], str) or not record["content"].strip():
        raise DatasetValidationError("memory.content must be non-empty")
    _require_unit_interval(record["importance"], "memory.importance")
    _require_unit_interval(record["confidence"], "memory.confidence")
    provenance = record["provenance"]
    if not isinstance(provenance, dict) or set(provenance) != {"source_type", "source_id", "note"}:
        raise DatasetValidationError("memory.provenance has an invalid schema")
    if provenance["source_type"] not in {item.value for item in SourceType}:
        raise DatasetValidationError("memory.provenance.source_type is invalid")
    if not all(
        isinstance(provenance[field], str) and provenance[field].strip()
        for field in ("source_id", "note")
    ):
        raise DatasetValidationError("memory.provenance values must be non-empty strings")


def _validate_query(record: Mapping[str, Any]) -> None:
    _require_exact_fields(record, _QUERY_FIELDS, "query")
    _require_id(record["query_id"], "query.query_id")
    _require_id(record["episode_id"], "query.episode_id")
    _require_id(record["owner_id"], "query.owner_id")
    if record["split"] not in _SPLITS or record["kind"] not in _KINDS:
        raise DatasetValidationError("query split or kind is invalid")
    if record["expected_behavior"] not in _BEHAVIORS:
        raise DatasetValidationError("query.expected_behavior is invalid")
    if not isinstance(record["query"], str) or not record["query"].strip():
        raise DatasetValidationError("query.query must be non-empty")
    if not isinstance(record["filters"], dict) or set(record["filters"]) - {
        "space",
        "type",
        "state",
    }:
        raise DatasetValidationError("query.filters has unsupported fields")
    if any(not isinstance(value, str) or not value for value in record["filters"].values()):
        raise DatasetValidationError("query.filters values must be non-empty strings")
    if record["expected_behavior"] == "abstain" and record["kind"] not in {
        "negative",
        "hard_negative",
    }:
        raise DatasetValidationError("abstention queries must be negative or hard_negative")


def _canonical_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_retrieval_dataset(dataset_dir: Path) -> DatasetValidationSummary:
    """Validate the frozen ``retrieval-v0`` JSONL files and manifest checksums."""
    memories = _read_jsonl(dataset_dir / "memories.jsonl")
    queries = _read_jsonl(dataset_dir / "queries.jsonl")
    relevance = _read_jsonl(dataset_dir / "relevance.jsonl")
    for memory in memories:
        _validate_memory(memory)
    for query in queries:
        _validate_query(query)
    memory_ids = _unique(memories, "memory_id", "memory")
    query_ids = _unique(queries, "query_id", "query")
    memory_by_id = {record["memory_id"]: record for record in memories}
    query_by_id = {record["query_id"]: record for record in queries}

    episode_splits: dict[str, str] = {}
    episode_owners: dict[str, str] = {}
    for record in [*memories, *queries]:
        episode_id, split, owner_id = record["episode_id"], record["split"], record["owner_id"]
        if episode_splits.setdefault(episode_id, split) != split:
            raise DatasetValidationError(f"episode {episode_id} crosses splits")
        if episode_owners.setdefault(episode_id, owner_id) != owner_id:
            raise DatasetValidationError(f"episode {episode_id} has multiple owners")
    if len(episode_splits) != 25 or Counter(episode_splits.values()) != {
        "development": 20,
        "holdout": 5,
    }:
        raise DatasetValidationError("dataset must contain 20 development and 5 holdout episodes")
    if len(memories) < 100 or len(queries) != 50:
        raise DatasetValidationError(
            "dataset requires at least 100 memories and exactly 50 queries"
        )

    seen_pairs: set[tuple[str, str]] = set()
    relevance_by_query: dict[str, list[Mapping[str, Any]]] = {}
    for record in relevance:
        _require_exact_fields(record, _RELEVANCE_FIELDS, "relevance")
        query_id = _require_id(record["query_id"], "relevance.query_id")
        memory_id = _require_id(record["memory_id"], "relevance.memory_id")
        if query_id not in query_ids or memory_id not in memory_ids:
            raise DatasetValidationError("relevance references an unknown record")
        if (query_id, memory_id) in seen_pairs:
            raise DatasetValidationError("duplicate relevance pair")
        seen_pairs.add((query_id, memory_id))
        if (
            not isinstance(record["grade"], int)
            or isinstance(record["grade"], bool)
            or record["grade"] not in {0, 1, 2}
        ):
            raise DatasetValidationError("relevance.grade must be 0, 1, or 2")
        if not isinstance(record["reason"], str) or not record["reason"].strip():
            raise DatasetValidationError("relevance.reason must be non-empty")
        query = query_by_id[query_id]
        memory = memory_by_id[memory_id]
        if query["split"] != memory["split"] or query["owner_id"] != memory["owner_id"]:
            raise DatasetValidationError("relevance pair crosses owner or split")
        relevance_by_query.setdefault(query_id, []).append(record)

    behaviors = Counter(record["expected_behavior"] for record in queries)
    if behaviors != {"retrieve": 35, "abstain": 15}:
        raise DatasetValidationError("dataset requires 35 retrieve and 15 abstain queries")
    cross_domain = [record for record in queries if record["kind"] == "cross_domain"]
    if len(cross_domain) < 10:
        raise DatasetValidationError("dataset requires at least 10 cross_domain queries")
    holdout = [record for record in queries if record["split"] == "holdout"]
    if len(holdout) < 10 or sum(q["expected_behavior"] == "abstain" for q in holdout) < 3:
        raise DatasetValidationError("holdout requires at least 10 queries and 3 abstentions")
    if sum(q["kind"] == "cross_domain" for q in holdout) < 2:
        raise DatasetValidationError("holdout requires at least 2 cross_domain queries")
    for query in queries:
        labels = relevance_by_query.get(query["query_id"], [])
        if query["expected_behavior"] == "retrieve" and not any(
            label["grade"] > 0 for label in labels
        ):
            raise DatasetValidationError(
                f"retrieve query {query['query_id']} lacks a positive label"
            )
        if query["expected_behavior"] == "abstain" and any(label["grade"] > 0 for label in labels):
            raise DatasetValidationError(f"abstain query {query['query_id']} has a positive label")

    manifest_path = dataset_dir / "checksums.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DatasetValidationError("checksums.json is invalid") from exc
    expected_names = {"memories.jsonl", "queries.jsonl", "relevance.jsonl"}
    if set(manifest) != expected_names:
        raise DatasetValidationError("checksums.json must list exactly the dataset JSONL files")
    for name in expected_names:
        if manifest[name] != _canonical_digest(dataset_dir / name):
            raise DatasetValidationError(f"checksum mismatch for {name}")
    return DatasetValidationSummary(
        memories=len(memories),
        queries=len(queries),
        relevance_pairs=len(relevance),
        episodes_by_split=dict(Counter(episode_splits.values())),
        queries_by_split=dict(Counter(record["split"] for record in queries)),
        query_behavior_counts=dict(behaviors),
        cross_domain_queries=len(cross_domain),
    )
