"""Mapping from the shared application service DTOs to MCP v0 DTOs."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from omp.application.models import (
    ForgetMemoryCommand,
    SearchFilters,
    SearchMemoryCommand,
    UpdateMemoryCommand,
    WriteMemoryCommand,
)
from omp.application.services import MemoryApplicationService
from omp.domain import MemoryState, MemoryType, Provenance, SourceType


class MemoryApplicationGateway:
    """Adapter for ``MemoryApplicationService``; it contains no business rules."""

    def __init__(self, service: MemoryApplicationService) -> None:
        self.service = service

    async def write(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = await self.service.write(
            WriteMemoryCommand(
                owner_id=payload["owner_id"],
                content=payload["content"],
                memory_type=MemoryType(payload["type"]),
                provenance=_provenance(payload["provenance"]),
                importance=payload.get("importance", 0.5),
                confidence=payload.get("confidence", 0.5),
                space=payload.get("space"),
                idempotency_key=payload.get("idempotency_key"),
            )
        )
        return {
            "memory": _memory(result.memory),
            "status": "created" if result.created else "already_exists",
        }

    async def search(self, payload: dict[str, Any]) -> dict[str, Any]:
        states = (
            frozenset({MemoryState(payload["state"])})
            if payload.get("state")
            else frozenset({MemoryState.ACTIVE})
        )
        types = frozenset({MemoryType(payload["type"])}) if payload.get("type") else None
        result = await self.service.search(
            SearchMemoryCommand(
                owner_id=payload["owner_id"],
                query=payload["query"],
                filters=SearchFilters(
                    states=states, memory_types=types, space=payload.get("space")
                ),
                limit=payload.get("limit", 10),
                candidate_limit=max(payload.get("limit", 10), 50),
                threshold=payload.get("min_relevance", 0.78),
            )
        )
        return {
            "items": [
                {
                    "memory": _memory(item.memory),
                    "score": item.score,
                    "reason_retrieved": item.reason_retrieved,
                    "profile_id": item.profile_id,
                    "profile_version": item.profile_version,
                }
                for item in result.items
            ],
            "profile_id": result.profile_id,
            "profile_version": result.profile_version,
        }

    async def update(self, payload: dict[str, Any]) -> dict[str, Any]:
        patch = payload.get("patch", {})
        command = UpdateMemoryCommand(
            owner_id=payload["owner_id"],
            memory_id=UUID(payload["id"]),
            expected_version=payload["expected_version"],
            content=patch.get("content"),
            memory_type=MemoryType(patch["type"]) if patch.get("type") else None,
            importance=patch.get("importance"),
            confidence=patch.get("confidence"),
            state=MemoryState(patch["state"]) if patch.get("state") else None,
            space=patch.get("space"),
            provenance=_provenance(patch["provenance"])
            if patch.get("provenance")
            else (_provenance(payload["provenance"]) if payload.get("provenance") else None),
            change_reason="updated",
            idempotency_key=payload.get("idempotency_key"),
        )
        result = await self.service.update(command)
        return {"memory": _memory(result), "status": "updated"}

    async def forget(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = await self.service.forget(
            ForgetMemoryCommand(
                owner_id=payload["owner_id"],
                memory_id=UUID(payload["id"]),
                idempotency_key=payload.get("idempotency_key"),
            )
        )
        return {"status": "forgotten" if result.forgotten else "already_absent"}


def _provenance(payload: dict[str, Any]) -> Provenance:
    source_type = payload["source_type"]
    if source_type == "other":
        source_type = "unknown"
    return Provenance(
        source_type=SourceType(source_type),
        source_id=payload.get("source_id"),
        source_model=payload.get("source_model"),
        captured_at=_datetime(payload["captured_at"]),
        evidence=(payload["evidence"],) if payload.get("evidence") else (),
    )


def _datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _memory(memory: Any) -> dict[str, Any]:
    provenance = memory.provenance
    return {
        "id": str(memory.id),
        "owner_id": memory.owner_id,
        "content": memory.content,
        "type": memory.memory_type.value,
        "space": memory.space,
        "importance": memory.importance,
        "confidence": memory.confidence,
        "state": memory.state.value,
        "version": memory.version,
        "created_at": memory.created_at.isoformat().replace("+00:00", "Z"),
        "updated_at": memory.updated_at.isoformat().replace("+00:00", "Z"),
        "occurred_at": memory.occurred_at.isoformat().replace("+00:00", "Z")
        if memory.occurred_at
        else None,
        "provenance": {
            "source_type": provenance.source_type.value
            if provenance.source_type.value != "unknown"
            else "unknown",
            "captured_at": provenance.captured_at.isoformat().replace("+00:00", "Z"),
            "source_id": provenance.source_id,
            "source_model": provenance.source_model,
            "evidence": " ".join(provenance.evidence) if provenance.evidence else None,
        },
    }
