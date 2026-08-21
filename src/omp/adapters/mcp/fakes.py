"""Deterministic local application-service fake used until the core is available.

This module is a test/integration harness, not a second domain implementation.
The production adapter accepts an injected application service with the same
operation names and never depends on this fake.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from .errors import NotFoundError, VersionConflictError


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


class InMemoryMemoryService:
    """Small deterministic service fake for contract and E2E tests."""

    def __init__(self) -> None:
        self.records: dict[str, dict[str, Any]] = {}
        self.idempotency: dict[tuple[str, str, str], str] = {}
        self.forget_keys: set[tuple[str, str]] = set()

    def write(self, payload: dict[str, Any]) -> dict[str, Any]:
        owner = payload["owner_id"]
        idem = payload["idempotency_key"]
        previous = self.idempotency.get((owner, "write", idem))
        if previous:
            return {"memory": dict(self.records[previous]), "status": "already_exists"}
        memory_id = "mem_" + uuid.uuid4().hex
        now = _now()
        record = {
            "id": memory_id,
            "owner_id": owner,
            "content": payload["content"],
            "type": payload["type"],
            "space": payload.get("space"),
            "importance": payload.get("importance", 0.5),
            "confidence": payload.get("confidence", 0.5),
            "state": "active",
            "version": 1,
            "created_at": now,
            "updated_at": now,
            "occurred_at": None,
            "provenance": payload["provenance"],
        }
        self.records[memory_id] = record
        self.idempotency[(owner, "write", idem)] = memory_id
        return {"memory": dict(record), "status": "created"}

    def search(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        query_tokens = _tokens(payload["query"])
        aliases = {
            "gtm": {
                "go",
                "to",
                "market",
                "strategy",
                "acquisition",
                "geographic",
                "density",
                "region",
            },
            "marketplace": {"marketplace", "network", "density", "geographic", "region"},
            "city": {"geographic", "region", "density"},
        }
        expanded = set(query_tokens)
        for token in query_tokens:
            expanded.update(aliases.get(token, set()))
        results: list[dict[str, Any]] = []
        for record in self.records.values():
            if record["owner_id"] != payload["owner_id"]:
                continue
            if record["state"] != payload.get("state", "active"):
                continue
            if payload.get("space") is not None and record.get("space") != payload["space"]:
                continue
            if payload.get("type") is not None and record["type"] != payload["type"]:
                continue
            content_tokens = _tokens(record["content"])
            direct = len(query_tokens & content_tokens)
            conceptual = len((expanded - query_tokens) & content_tokens)
            if not direct and not conceptual:
                continue
            score = min(
                1.0, 0.65 + (direct * 0.1) + (conceptual * 0.08) + record["importance"] * 0.1
            )
            if score < payload.get("min_relevance", 0):
                continue
            results.append({"memory": dict(record), "score": round(score, 6)})
        results.sort(key=lambda item: (-item["score"], item["memory"]["created_at"]))
        return results[: payload["limit"]]

    def get(self, *, owner_id: str, memory_id: str) -> dict[str, Any] | None:
        record = self.records.get(memory_id)
        if record is None or record["owner_id"] != owner_id:
            return None
        return dict(record)

    def update(self, payload: dict[str, Any]) -> dict[str, Any]:
        memory_id = payload["id"]
        record = self.records.get(memory_id)
        if record is None or record["owner_id"] != payload["owner_id"]:
            raise NotFoundError()
        if record["version"] != payload["expected_version"]:
            raise VersionConflictError()
        for key, value in payload["patch"].items():
            if value is not None:
                record[key] = value
        if payload.get("provenance") is not None:
            record["provenance"] = payload["provenance"]
        record["version"] += 1
        record["updated_at"] = _now()
        return {"memory": dict(record), "status": "updated"}

    def forget(self, payload: dict[str, Any]) -> dict[str, Any]:
        key = (payload["owner_id"], payload["id"])
        if key in self.forget_keys:
            return {"status": "already_absent"}
        record = self.records.get(payload["id"])
        if record is None or record["owner_id"] != payload["owner_id"]:
            self.forget_keys.add(key)
            return {"status": "already_absent"}
        del self.records[payload["id"]]
        self.forget_keys.add(key)
        return {"status": "forgotten"}

    def export_records(
        self, owner_id: str | None = None, include_embeddings: bool = False
    ) -> list[dict[str, Any]]:
        del include_embeddings  # The fake has no embeddings and never invents them.
        return [
            dict(record)
            for record in self.records.values()
            if owner_id is None or record["owner_id"] == owner_id
        ]

    def import_records(self, records: list[dict[str, Any]]) -> int:
        incoming_ids: set[str] = set()
        for incoming in records:
            memory_id = incoming["id"]
            if memory_id in incoming_ids:
                raise VersionConflictError()
            incoming_ids.add(memory_id)
            current = self.records.get(memory_id)
            if current is not None and current != incoming:
                raise VersionConflictError()
        imported = 0
        for incoming in records:
            memory_id = incoming["id"]
            current = self.records.get(memory_id)
            if current == incoming:
                continue
            self.records[memory_id] = dict(incoming)
            imported += 1
        return imported


def _tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9À-ÿ]+", value.casefold()))


def stable_owner_hash(owner_id: str) -> str:
    """For local diagnostics only; never use the raw owner ID in logs."""

    return hashlib.sha256(owner_id.encode("utf-8")).hexdigest()[:12]
