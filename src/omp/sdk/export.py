"""Open, versioned export/import package validation."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from omp.adapters.mcp.schemas import MemoryRecord, StrictModel


class EmbeddingProfileRecord(StrictModel):
    profile_id: str = Field(min_length=1, max_length=128)
    profile_version: str = Field(min_length=1, max_length=64)
    dimension: int = Field(ge=1, le=16_384)
    metric: str = Field(pattern=r"^(cosine|l2|inner_product)$")


class HistoryRecord(StrictModel):
    memory_id: str = Field(min_length=1, max_length=128)
    version: int = Field(ge=1)
    content: str = Field(min_length=1, max_length=16_384)
    type: str = Field(min_length=1, max_length=64)
    state: str = Field(min_length=1, max_length=64)
    importance: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    space: str | None = Field(default=None, max_length=128)
    occurred_at: str | None = Field(default=None, max_length=80)
    provenance: dict[str, Any]
    changed_at: str = Field(min_length=1, max_length=80)
    change_reason: str = Field(min_length=1, max_length=256)


class RelationRecord(StrictModel):
    source_id: str = Field(min_length=1, max_length=128)
    target_id: str = Field(min_length=1, max_length=128)
    type: str = Field(min_length=1, max_length=64)
    owner_id: str = Field(min_length=1, max_length=256)
    created_at: str = Field(min_length=1, max_length=80)


class ExportMemoryRecord(MemoryRecord):
    """Wire representation of the application export DTO.

    The current memory fields remain flat for compatibility with the local
    harness. History, relations, embedding profile and the write fingerprint
    are carried as versioned administrative metadata. Vector values are
    omitted unless an explicit opt-in requests them.
    """

    idempotency_key: str | None = Field(default=None, max_length=256)
    provenance_evidence: list[str] = Field(default_factory=list)
    embedding_profile: EmbeddingProfileRecord | None = None
    history: list[HistoryRecord] = Field(default_factory=list)
    relations: list[RelationRecord] = Field(default_factory=list)
    embedding_values: list[float] | None = None
    write_fingerprint: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class ExportDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    format: str = Field(pattern=r"^omp\.export\.v0$")
    exported_at: str = Field(min_length=1, max_length=80)
    includes_embeddings: bool = False
    memories: list[ExportMemoryRecord]

    @field_validator("exported_at")
    @classmethod
    def timestamp(cls, value: str) -> str:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("exported_at must include a timezone")
        return parsed.astimezone(UTC).isoformat().replace("+00:00", "Z")

    @field_validator("memories")
    @classmethod
    def unique_ids(cls, value: list[ExportMemoryRecord]) -> list[ExportMemoryRecord]:
        ids = [item.id for item in value]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate memory id")
        return value


def make_export(
    records: list[dict[str, Any]], *, include_embeddings: bool = False
) -> dict[str, Any]:
    if include_embeddings and any(
        item.get("embedding_values") is None for item in records
    ):
        raise ValueError("embedding values are missing from the export response")
    document = ExportDocument(
        format="omp.export.v0",
        exported_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        includes_embeddings=include_embeddings,
        memories=[ExportMemoryRecord.model_validate(record) for record in records],
    )
    return document.model_dump(mode="json", exclude_none=True)


def load_export(path: str | Path) -> ExportDocument:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return ExportDocument.model_validate(payload)
    except (OSError, ValueError, ValidationError) as exc:
        raise ValueError("invalid OMP export package") from exc


def write_export(
    path: str | Path, records: list[dict[str, Any]], *, include_embeddings: bool = False
) -> ExportDocument:
    document = ExportDocument.model_validate(
        make_export(records, include_embeddings=include_embeddings)
    )
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(
            document.model_dump(mode="json", exclude_none=True),
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return document
