"""Reproducible PostgreSQL/pgvector retrieval evaluation runner.

It deliberately calls the MCP application gateway, not repository internals,
and emits identifiers only in reports so artifacts never reproduce corpus text.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import platform
import subprocess
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from uuid import UUID

from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from omp import __version__
from omp.adapters.embeddings import HashEmbeddingProvider
from omp.adapters.mcp.application_gateway import MemoryApplicationGateway
from omp.adapters.postgres import create_postgres_uow_factory
from omp.application.models import UpdateMemoryCommand
from omp.application.services import MemoryApplicationService
from omp.config import OMPSettings
from omp.domain import MemoryState

from .dataset import validate_retrieval_dataset
from .metrics import QueryOutcome, aggregate_metrics, slice_metrics


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def load_config(path: Path) -> dict[str, Any]:
    """Parse the intentionally flat, dependency-free evaluation YAML format."""
    result: dict[str, Any] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, separator, raw_value = line.partition(":")
        if not separator or not key.strip() or not raw_value.strip():
            raise ValueError(f"invalid eval config line: {line!r}")
        value = raw_value.strip()
        if value.isdigit():
            result[key.strip()] = int(value)
        else:
            try:
                result[key.strip()] = float(value)
            except ValueError:
                result[key.strip()] = value
    required = {
        "dataset",
        "profile_id",
        "profile_version",
        "dimension",
        "threshold",
        "candidate_limit",
        "result_limit",
        "warmups",
        "runs",
        "p95_budget_ms",
    }
    missing = required - set(result)
    if missing:
        raise ValueError(f"eval config missing: {', '.join(sorted(missing))}")
    return result


def _git_metadata(root: Path) -> dict[str, Any]:
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True, capture_output=True, check=False
    )
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=root, text=True, capture_output=True, check=False
    )
    return {
        "revision": revision.stdout.strip() if revision.returncode == 0 else "UNBORN",
        "dirty": bool(status.stdout.strip()),
    }


def _percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int((len(ordered) - 1) * fraction + 0.999999)))
    return round(ordered[index], 3)


async def _database_versions(engine: Any) -> dict[str, str]:
    async with engine.connect() as connection:
        postgres = str(await connection.scalar(text("SHOW server_version")))
        pgvector = str(
            await connection.scalar(
                text("SELECT extversion FROM pg_extension WHERE extname='vector'")
            )
        )
    return {"postgresql": postgres, "pgvector": pgvector}


async def _truncate(engine: Any) -> None:
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "TRUNCATE TABLE idempotency_operations, memory_relations, "
                "memory_embeddings, memory_versions, memories CASCADE"
            )
        )


async def _run_split(
    *,
    records: list[dict[str, Any]],
    queries: list[dict[str, Any]],
    config: dict[str, Any],
    gateway: MemoryApplicationGateway,
    service: MemoryApplicationService,
) -> tuple[list[QueryOutcome], list[float]]:
    ids: dict[str, str] = {}
    for record in records:
        created = await gateway.write(
            {
                "owner_id": record["owner_id"],
                "content": record["content"],
                "type": record["type"],
                "importance": record["importance"],
                "confidence": record["confidence"],
                "space": record["space"],
                "idempotency_key": f"eval-{record['memory_id']}",
                "provenance": {
                    "source_type": record["provenance"]["source_type"],
                    "source_id": record["provenance"]["source_id"],
                    "captured_at": "2026-01-01T00:00:00Z",
                    "evidence": None,
                },
            }
        )
        ids[record["memory_id"]] = created["memory"]["id"]
    # Production writes start active. Apply frozen lifecycle labels through the real service.
    active_by_episode = {
        record["episode_id"]: ids[record["memory_id"]]
        for record in records
        if record["state"] == "active"
    }
    for record in records:
        if record["state"] != "active":
            target_id = UUID(active_by_episode[record["episode_id"]])
            state = MemoryState(record["state"])
            update_args: dict[str, Any] = {"state": state}
            if state == MemoryState.SUPERSEDED:
                update_args = {"supersedes_memory_id": target_id}
            elif state == MemoryState.CONTRADICTED:
                update_args = {"contradicts_memory_id": target_id}
            await service.update(
                UpdateMemoryCommand(
                    owner_id=record["owner_id"],
                    memory_id=UUID(ids[record["memory_id"]]),
                    expected_version=1,
                    change_reason="eval fixture lifecycle",
                    **update_args,
                )
            )
    reverse_ids = {value: key for key, value in ids.items()}

    async def search(query: dict[str, Any]) -> tuple[QueryOutcome, float]:
        payload: dict[str, Any] = {
            "owner_id": query["owner_id"],
            "query": query["query"],
            "limit": config["result_limit"],
            "min_relevance": config["threshold"],
        }
        payload.update(query["filters"])
        start = time.perf_counter_ns()
        response = await gateway.search(payload)
        elapsed = (time.perf_counter_ns() - start) / 1_000_000
        failures: list[str] = []
        returned_ids: list[str] = []
        metadata: list[dict[str, str]] = []
        for item in response["items"]:
            memory = item["memory"]
            external_id = reverse_ids.get(memory["id"], "unknown")
            returned_ids.append(external_id)
            metadata.append(
                {
                    "memory_type": memory["type"],
                    "space": memory["space"] or "none",
                    "state": memory["state"],
                }
            )
            if memory["owner_id"] != query["owner_id"]:
                failures.append("owner")
            expected_state = query["filters"].get("state", "active")
            if memory["state"] != expected_state:
                failures.append("state")
            if query["filters"].get("space") and memory["space"] != query["filters"]["space"]:
                failures.append("space")
            if (
                item["profile_id"] != config["profile_id"]
                or item["profile_version"] != config["profile_version"]
            ):
                failures.append("profile")
        if (
            response["profile_id"] != config["profile_id"]
            or response["profile_version"] != config["profile_version"]
        ):
            failures.append("profile")
        return QueryOutcome(
            query["query_id"],
            query["split"],
            query["kind"],
            query["expected_behavior"],
            tuple(returned_ids),
            tuple(metadata),
            (),
            tuple(sorted(set(failures))),
        ), elapsed

    for _ in range(config["warmups"]):
        for query in queries:
            await search(query)
    measured: dict[str, QueryOutcome] = {}
    timings: list[float] = []
    for _ in range(config["runs"]):
        for query in queries:
            outcome, elapsed = await search(query)
            prior = measured.get(outcome.query_id)
            if prior is not None and prior.returned_ids != outcome.returned_ids:
                outcome = replace(
                    outcome,
                    deterministic_failures=tuple(
                        sorted(set(outcome.deterministic_failures + ("nondeterministic",)))
                    ),
                )
            measured[outcome.query_id] = outcome
            timings.append(elapsed)
    return list(measured.values()), timings


def _decision(
    metrics: dict[str, float | int], slices: dict[str, Any], p95: float, config: dict[str, Any]
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if metrics["precision_at_5"] < 0.80:
        reasons.append("precision_at_5 < 0.80")
    if metrics["intrusion_at_5"] > 0.10:
        reasons.append("intrusion_at_5 > 0.10")
    if metrics["abstention_rate"] < 0.90:
        reasons.append("abstention_rate < 0.90")
    if metrics["lifecycle_isolation_correctness"] != 1.0:
        reasons.append("deterministic lifecycle/isolation/profile failure")
    if p95 >= config["p95_budget_ms"]:
        reasons.append("p95 exceeds provisional budget")
    for name, value in slices["query_kind"].items():
        if value["positive_queries"] >= 5 and value["precision_at_5"] < 0.60:
            reasons.append(f"red positive slice query_kind={name}")
    return ("GO" if not reasons else "NO-GO"), reasons


def _markdown(report: dict[str, Any]) -> str:
    metrics = report["metrics"]
    return (
        "\n".join(
            [
                "# S04 retrieval evaluation — hash/v1",
                "",
                f"Decision: **{report['decision']}**",
                "",
                "## Gate metrics",
                "",
                "| Metric | Result | Gate |",
                "| --- | ---: | ---: |",
                f"| precision@5 | {metrics['precision_at_5']:.3f} | >= 0.800 |",
                f"| intrusion@5 | {metrics['intrusion_at_5']:.3f} | <= 0.100 |",
                f"| abstention | {metrics['abstention_rate']:.3f} | >= 0.900 |",
                "| lifecycle/isolation | "
                f"{metrics['lifecycle_isolation_correctness']:.3f} | 1.000 |",
                "| p95 (ms) | "
                f"{report['latency_ms']['p95']} | < {report['config']['p95_budget_ms']} |",
                "",
                "## Reasons",
                "",
                *(f"- {reason}" for reason in report["reasons"]),
                "",
                "Failure details are identifiers only in `report.json`; "
                "no corpus content is copied here.",
            ]
        )
        + "\n"
    )


async def run(config_path: Path, output_root: Path | None = None) -> Path:
    root = Path.cwd()
    config = load_config(config_path)
    dataset_dir = root / str(config["dataset"])
    validate_retrieval_dataset(dataset_dir)
    memories, queries, labels = (
        _jsonl(dataset_dir / name)
        for name in ("memories.jsonl", "queries.jsonl", "relevance.jsonl")
    )
    relevance: dict[str, dict[str, int]] = defaultdict(dict)
    for label in labels:
        relevance[label["query_id"]][label["memory_id"]] = label["grade"]
    settings = OMPSettings(
        database_url=SecretStr(
            os.environ.get("OMP_DATABASE_URL", OMPSettings().database_url.get_secret_value())
        ),
        embedding_profile_id=str(config["profile_id"]),
        embedding_profile_version=str(config["profile_version"]),
        embedding_dimension=int(config["dimension"]),
        retrieval_default_threshold=float(config["threshold"]),
        retrieval_default_candidate_limit=int(config["candidate_limit"]),
        retrieval_default_limit=int(config["result_limit"]),
    )
    factory, engine = create_postgres_uow_factory(settings)
    service = MemoryApplicationService(
        uow_factory=cast(Callable[[], Any], factory),
        embedding_provider=HashEmbeddingProvider(
            dimension=int(config["dimension"]),
            profile_id=str(config["profile_id"]),
            version=str(config["profile_version"]),
        ),
    )
    gateway = MemoryApplicationGateway(service)
    try:
        typed_engine = cast(AsyncEngine, engine)
        versions = await _database_versions(typed_engine)
        outcomes: list[QueryOutcome] = []
        timings: list[float] = []
        for split in ("development", "holdout"):
            await _truncate(typed_engine)
            split_outcomes, split_timings = await _run_split(
                records=[x for x in memories if x["split"] == split],
                queries=[x for x in queries if x["split"] == split],
                config=config,
                gateway=gateway,
                service=service,
            )
            outcomes.extend(split_outcomes)
            timings.extend(split_timings)
    finally:
        await typed_engine.dispose()
    memory_by_id = {record["memory_id"]: record for record in memories}
    outcomes = [
        replace(
            outcome,
            target_metadata=tuple(
                {
                    "memory_type": memory_by_id[memory_id]["type"],
                    "space": memory_by_id[memory_id]["space"],
                    "state": memory_by_id[memory_id]["state"],
                }
                for memory_id, grade in relevance[outcome.query_id].items()
                if grade > 0
            ),
        )
        for outcome in outcomes
    ]
    metrics = aggregate_metrics(outcomes, relevance)
    slices = slice_metrics(outcomes, relevance)
    p50, p95 = _percentile(timings, 0.50), _percentile(timings, 0.95)
    decision, reasons = _decision(metrics, slices, p95, config)
    failures = []
    for item in outcomes:
        failure_codes = list(item.deterministic_failures)
        relevant_ids = {
            memory_id for memory_id, grade in relevance[item.query_id].items() if grade > 0
        }
        intrusive_ids = {
            memory_id for memory_id, grade in relevance[item.query_id].items() if grade == 0
        }
        if item.expected_behavior == "retrieve" and not item.returned_ids:
            failure_codes.append("no_retrieval")
        elif item.expected_behavior == "retrieve" and not set(item.returned_ids) & relevant_ids:
            failure_codes.append("no_relevant_result")
        if set(item.returned_ids) & intrusive_ids:
            failure_codes.append("intrusion")
        if item.expected_behavior == "abstain" and item.returned_ids:
            failure_codes.append("abstention_failure")
        if failure_codes:
            failures.append(
                {
                    "query_id": item.query_id,
                    "failures": sorted(set(failure_codes)),
                    "returned_memory_ids": list(item.returned_ids),
                    "relevant_memory_ids": sorted(relevant_ids),
                }
            )
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    revision = _git_metadata(root)["revision"][:12]
    destination = (output_root or root / "evals" / "reports") / f"{stamp}-{revision}-hash-v1"
    destination.mkdir(parents=True, exist_ok=False)
    report: dict[str, Any] = {
        "schema_version": 1,
        "decision": decision,
        "reasons": reasons,
        "git": _git_metadata(root),
        "dataset": {
            "name": dataset_dir.name,
            "sha256": {
                name: _sha256(dataset_dir / name)
                for name in ("memories.jsonl", "queries.jsonl", "relevance.jsonl", "checksums.json")
            },
        },
        "config": {**config, "sha256": _sha256(config_path)},
        "versions": {"python": platform.python_version(), "omp": __version__, **versions},
        "environment": {
            "platform": platform.platform(),
            "backend": "postgresql+pgvector",
            "single_client": True,
        },
        "runs": {
            "warmups": config["warmups"],
            "runs": config["runs"],
            "measured_searches": len(timings),
        },
        "metrics": metrics,
        "slices": slices,
        "latency_ms": {"p50": p50, "p95": p95, "budget_ms": config["p95_budget_ms"]},
        "external_cost": {
            "currency": "USD",
            "amount": 0.0,
            "reason": "hash/v1 is local and has no external embedding calls",
        },
        "failures": failures,
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
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args()
    print(asyncio.run(run(args.config, args.output_root)))


if __name__ == "__main__":
    main()
