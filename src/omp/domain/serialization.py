"""Versioned, transport-independent serialization for domain fixtures."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any
from uuid import UUID

from .errors import ValidationError
from .memory import Memory
from .types import EmbeddingDescriptor, MemoryState, MemoryType, Provenance, SourceType

SCHEMA_VERSION = 1


def _datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def memory_to_dict(memory: Memory) -> dict[str, object]:
    provenance = memory.provenance
    embedding = memory.embedding
    return {
        "schema_version": SCHEMA_VERSION,
        "id": str(memory.id),
        "owner_id": memory.owner_id,
        "content": memory.content,
        "type": memory.memory_type.value,
        "importance": memory.importance,
        "confidence": memory.confidence,
        "state": memory.state.value,
        "version": memory.version,
        "created_at": memory.created_at.isoformat(),
        "updated_at": memory.updated_at.isoformat(),
        "occurred_at": _datetime(memory.occurred_at),
        "space": memory.space,
        "provenance": {
            "source_type": provenance.source_type.value,
            "source_id": provenance.source_id,
            "source_model": provenance.source_model,
            "captured_at": provenance.captured_at.isoformat(),
            "evidence": list(provenance.evidence),
        },
        "embedding": (
            {
                "profile_id": embedding.profile_id,
                "profile_version": embedding.profile_version,
                "dimension": embedding.dimension,
                "metric": embedding.metric,
            }
            if embedding
            else None
        ),
        "idempotency_key": memory.idempotency_key,
    }


def memory_from_dict(payload: Mapping[str, Any]) -> Memory:
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValidationError("unsupported memory schema_version")
    try:
        provenance_payload = payload["provenance"]
        if not isinstance(provenance_payload, Mapping):
            raise TypeError
        embedding_payload = payload.get("embedding")
        embedding = (
            EmbeddingDescriptor(
                profile_id=str(embedding_payload["profile_id"]),
                profile_version=str(embedding_payload["profile_version"]),
                dimension=int(embedding_payload["dimension"]),
                metric=str(embedding_payload["metric"]),
            )
            if isinstance(embedding_payload, Mapping)
            else None
        )
        return Memory(
            id=UUID(str(payload["id"])),
            owner_id=str(payload["owner_id"]),
            content=str(payload["content"]),
            memory_type=MemoryType(str(payload["type"])),
            importance=float(payload["importance"]),
            confidence=float(payload["confidence"]),
            state=MemoryState(str(payload["state"])),
            version=int(payload["version"]),
            created_at=datetime.fromisoformat(str(payload["created_at"])),
            updated_at=datetime.fromisoformat(str(payload["updated_at"])),
            occurred_at=(
                datetime.fromisoformat(str(payload["occurred_at"]))
                if payload.get("occurred_at")
                else None
            ),
            space=str(payload["space"]) if payload.get("space") is not None else None,
            provenance=Provenance(
                source_type=SourceType(str(provenance_payload["source_type"])),
                source_id=(
                    str(provenance_payload["source_id"])
                    if provenance_payload.get("source_id") is not None
                    else None
                ),
                source_model=(
                    str(provenance_payload["source_model"])
                    if provenance_payload.get("source_model") is not None
                    else None
                ),
                captured_at=datetime.fromisoformat(str(provenance_payload["captured_at"])),
                evidence=tuple(str(item) for item in provenance_payload.get("evidence", [])),
            ),
            embedding=embedding,
            idempotency_key=(
                str(payload["idempotency_key"])
                if payload.get("idempotency_key") is not None
                else None
            ),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValidationError("invalid memory serialization") from exc
