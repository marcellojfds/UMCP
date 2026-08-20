"""Lane-B administrative codecs for the versioned export package."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from omp.application.models import MemoryImportRecord
from omp.domain import (
    EmbeddingDescriptor,
    Memory,
    MemoryState,
    MemoryType,
    MemoryVersion,
    Provenance,
    Relation,
    RelationType,
    SourceType,
)
from omp.sdk.export import ExportMemoryRecord


def export_record_payload(record: Any, *, include_embeddings: bool = False) -> dict[str, Any]:
    """Serialize a real ``MemoryExportRecord`` without exposing vector data by default."""

    memory = record.memory
    payload: dict[str, Any] = _memory_payload(memory)
    payload["history"] = [_version_payload(item) for item in record.history]
    payload["relations"] = [_relation_payload(item) for item in record.relations]
    if record.write_fingerprint is not None:
        payload["write_fingerprint"] = record.write_fingerprint
    if include_embeddings and record.embedding is not None:
        payload["embedding_values"] = list(record.embedding)
    return payload


def import_record(record: ExportMemoryRecord) -> MemoryImportRecord:
    """Map a validated export record to the core's real import DTO."""

    return MemoryImportRecord(
        memory=_memory_from_payload(record.model_dump(mode="python")),
        history=tuple(
            _version_from_payload(item.model_dump(mode="python")) for item in record.history
        ),
        relations=tuple(
            _relation_from_payload(item.model_dump(mode="python")) for item in record.relations
        ),
        embedding=(tuple(record.embedding_values) if record.embedding_values is not None else None),
        write_fingerprint=record.write_fingerprint,
    )


def _timestamp(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _provenance_payload(value: Any) -> dict[str, Any]:
    return {
        "source_type": value.source_type.value,
        "captured_at": _timestamp(value.captured_at),
        "source_id": value.source_id,
        "source_model": value.source_model,
        "evidence": list(value.evidence),
    }


def _memory_payload(value: Any) -> dict[str, Any]:
    embedding = value.embedding
    provenance = _provenance_payload(value.provenance)
    provenance["evidence"] = (
        " ".join(value.provenance.evidence) if value.provenance.evidence else None
    )
    return {
        "id": str(value.id),
        "owner_id": value.owner_id,
        "content": value.content,
        "type": value.memory_type.value,
        "space": value.space,
        "importance": value.importance,
        "confidence": value.confidence,
        "state": value.state.value,
        "version": value.version,
        "created_at": _timestamp(value.created_at),
        "updated_at": _timestamp(value.updated_at),
        "occurred_at": _timestamp(value.occurred_at) if value.occurred_at else None,
        "provenance": provenance,
        "provenance_evidence": list(value.provenance.evidence),
        "idempotency_key": value.idempotency_key,
        "embedding_profile": (
            {
                "profile_id": embedding.profile_id,
                "profile_version": embedding.profile_version,
                "dimension": embedding.dimension,
                "metric": embedding.metric,
            }
            if embedding is not None
            else None
        ),
    }


def _version_payload(value: Any) -> dict[str, Any]:
    return {
        "memory_id": str(value.memory_id),
        "version": value.version,
        "content": value.content,
        "type": value.memory_type.value,
        "state": value.state.value,
        "importance": value.importance,
        "confidence": value.confidence,
        "space": value.space,
        "occurred_at": _timestamp(value.occurred_at) if value.occurred_at else None,
        "provenance": _provenance_payload(value.provenance),
        "changed_at": _timestamp(value.changed_at),
        "change_reason": value.change_reason,
    }


def _relation_payload(value: Any) -> dict[str, Any]:
    return {
        "source_id": str(value.source_id),
        "target_id": str(value.target_id),
        "type": value.relation_type.value,
        "owner_id": value.owner_id,
        "created_at": _timestamp(value.created_at),
    }


def _parse_time(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


def _required_time(value: str) -> datetime:
    parsed = _parse_time(value)
    if parsed is None:
        raise ValueError("timestamp is required")
    return parsed


def _provenance_from_payload(value: dict[str, Any]) -> Provenance:
    evidence = value.get("evidence", ())
    if isinstance(evidence, str):
        evidence = (evidence,)
    if not isinstance(evidence, list | tuple):
        raise ValueError("invalid provenance evidence")
    source_type = str(value["source_type"])
    if source_type == "other":
        source_type = "unknown"
    return Provenance(
        source_type=SourceType(source_type),
        captured_at=_required_time(str(value["captured_at"])),
        source_id=value.get("source_id"),
        source_model=value.get("source_model"),
        evidence=tuple(str(item) for item in evidence),
    )


def _memory_from_payload(value: dict[str, Any]) -> Memory:
    profile = value.get("embedding_profile")
    embedding = (
        EmbeddingDescriptor(
            profile_id=str(profile["profile_id"]),
            profile_version=str(profile["profile_version"]),
            dimension=int(profile["dimension"]),
            metric=str(profile["metric"]),
        )
        if isinstance(profile, dict)
        else None
    )
    provenance_payload = dict(value["provenance"])
    if value.get("provenance_evidence") is not None:
        provenance_payload["evidence"] = value["provenance_evidence"]
    return Memory(
        id=UUID(str(value["id"])),
        owner_id=str(value["owner_id"]),
        content=str(value["content"]),
        memory_type=MemoryType(str(value["type"])),
        importance=float(value["importance"]),
        confidence=float(value["confidence"]),
        state=MemoryState(str(value["state"])),
        version=int(value["version"]),
        created_at=_required_time(str(value["created_at"])),
        updated_at=_required_time(str(value["updated_at"])),
        occurred_at=_parse_time(value.get("occurred_at")),
        space=value.get("space"),
        provenance=_provenance_from_payload(provenance_payload),
        embedding=embedding,
        idempotency_key=value.get("idempotency_key"),
    )


def _version_from_payload(value: dict[str, Any]) -> MemoryVersion:
    return MemoryVersion(
        memory_id=UUID(str(value["memory_id"])),
        version=int(value["version"]),
        content=str(value["content"]),
        memory_type=MemoryType(str(value["type"])),
        state=MemoryState(str(value["state"])),
        importance=float(value["importance"]),
        confidence=float(value["confidence"]),
        space=value.get("space"),
        occurred_at=_parse_time(value.get("occurred_at")),
        provenance=_provenance_from_payload(value["provenance"]),
        changed_at=_required_time(str(value["changed_at"])),
        change_reason=str(value["change_reason"]),
    )


def _relation_from_payload(value: dict[str, Any]) -> Relation:
    return Relation(
        source_id=UUID(str(value["source_id"])),
        target_id=UUID(str(value["target_id"])),
        relation_type=RelationType(str(value["type"])),
        owner_id=str(value["owner_id"]),
        created_at=_required_time(str(value["created_at"])),
    )
