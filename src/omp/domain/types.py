"""Canonical enums and value objects for memory semantics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Final
from uuid import UUID

from .errors import ValidationError


class MemoryType(StrEnum):
    FACT = "fact"
    PREFERENCE = "preference"
    DECISION = "decision"
    INSIGHT = "insight"
    HYPOTHESIS = "hypothesis"
    LESSON = "lesson"
    GOAL = "goal"
    PROJECT_CONTEXT = "project_context"
    CONCEPT = "concept"
    RELATIONSHIP = "relationship"
    OPEN_QUESTION = "open_question"


class MemoryState(StrEnum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    CONTRADICTED = "contradicted"
    ARCHIVED = "archived"


class RelationType(StrEnum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    DERIVED_FROM = "derived_from"
    RELATED_TO = "related_to"
    SUPERSEDES = "supersedes"
    APPLIES_TO = "applies_to"


class SourceType(StrEnum):
    USER = "user"
    AGENT = "agent"
    CONVERSATION = "conversation"
    IMPORT = "import"
    SYSTEM = "system"
    UNKNOWN = "unknown"


MAX_OWNER_ID_LENGTH: Final = 256
MAX_SPACE_LENGTH: Final = 256
MAX_IDEMPOTENCY_KEY_LENGTH: Final = 256


def utc_now() -> datetime:
    return datetime.now(UTC)


def ensure_aware(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValidationError(f"{field_name} must be timezone-aware")
    return value.astimezone(UTC)


def validate_owner_id(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("owner_id must be a non-empty string")
    normalized = value.strip()
    if len(normalized) > MAX_OWNER_ID_LENGTH:
        raise ValidationError("owner_id exceeds the maximum length")
    return normalized


def validate_space(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized or len(normalized) > MAX_SPACE_LENGTH:
        raise ValidationError("space must be empty or within the maximum length")
    return normalized


def validate_idempotency_key(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized or len(normalized) > MAX_IDEMPOTENCY_KEY_LENGTH:
        raise ValidationError("idempotency_key must be non-empty and within the maximum length")
    return normalized


def validate_unit_interval(value: float, field_name: str) -> float:
    if not isinstance(value, int | float) or not 0 <= float(value) <= 1:
        raise ValidationError(f"{field_name} must be between 0 and 1")
    return float(value)


@dataclass(frozen=True, slots=True)
class Provenance:
    """Minimal origin metadata; evidence is intentionally optional."""

    source_type: SourceType
    captured_at: datetime
    source_id: str | None = None
    source_model: str | None = None
    evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "captured_at", ensure_aware(self.captured_at, "captured_at"))
        if self.source_id is not None and not self.source_id.strip():
            raise ValidationError("source_id cannot be blank")
        if self.source_model is not None and not self.source_model.strip():
            raise ValidationError("source_model cannot be blank")
        if any(not item.strip() for item in self.evidence):
            raise ValidationError("provenance evidence cannot contain blank items")


@dataclass(frozen=True, slots=True)
class EmbeddingDescriptor:
    profile_id: str
    profile_version: str
    dimension: int
    metric: str = "cosine"

    def __post_init__(self) -> None:
        if not self.profile_id.strip() or not self.profile_version.strip():
            raise ValidationError("embedding profile id and version are required")
        if self.dimension <= 0:
            raise ValidationError("embedding dimension must be positive")
        if self.metric not in {"cosine", "l2", "inner_product"}:
            raise ValidationError("unsupported embedding metric")


@dataclass(frozen=True, slots=True)
class Relation:
    source_id: UUID
    target_id: UUID
    relation_type: RelationType
    owner_id: str
    created_at: datetime

    def __post_init__(self) -> None:
        validate_owner_id(self.owner_id)
        ensure_aware(self.created_at, "created_at")
        if self.source_id == self.target_id:
            raise ValidationError("a relation cannot point to itself")
