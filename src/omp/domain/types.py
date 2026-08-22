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
    MENTAL_NOTE = "mental_note"


class MemoryState(StrEnum):
    CANDIDATE = "candidate"
    CONFIRMED = "confirmed"
    PINNED = "pinned"
    STALE = "stale"
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


class ConsentMode(StrEnum):
    MANUAL = "manual"
    ASSISTED = "assisted"
    AUTOMATIC = "automatic"
    LEGACY_UNVERIFIED = "legacy_unverified"


class ConsentReason(StrEnum):
    USER_REQUESTED_MEMORY = "user_requested_memory"
    USER_CONFIRMED_INBOX = "user_confirmed_inbox"
    CONNECTION_POLICY_AUTOMATIC = "connection_policy_automatic"
    IMPORT_AUTHORIZED = "import_authorized"


MAX_OWNER_ID_LENGTH: Final = 256
MAX_SPACE_LENGTH: Final = 256
MAX_IDEMPOTENCY_KEY_LENGTH: Final = 256
MAX_OPAQUE_ID_LENGTH: Final = 256
MAX_EVIDENCE_ITEM_LENGTH: Final = 512


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
    source_client: str | None = None
    source_connection_id: str | None = None
    conversation_id: str | None = None
    message_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.source_type, SourceType):
            try:
                object.__setattr__(self, "source_type", SourceType(str(self.source_type)))
            except ValueError as exc:
                raise ValidationError("invalid provenance source_type") from exc
        object.__setattr__(self, "captured_at", ensure_aware(self.captured_at, "captured_at"))
        if self.source_id is not None and not self.source_id.strip():
            raise ValidationError("source_id cannot be blank")
        if self.source_model is not None and not self.source_model.strip():
            raise ValidationError("source_model cannot be blank")
        if any(not item.strip() for item in self.evidence):
            raise ValidationError("provenance evidence cannot contain blank items")
        for field_name in (
            "source_client",
            "source_connection_id",
            "conversation_id",
            "message_id",
        ):
            value = getattr(self, field_name)
            if value is not None:
                if not isinstance(value, str) or not value.strip():
                    raise ValidationError(f"{field_name} cannot be blank")
                if len(value) > MAX_OPAQUE_ID_LENGTH:
                    raise ValidationError(f"{field_name} exceeds the maximum length")
        if any(len(item) > MAX_EVIDENCE_ITEM_LENGTH for item in self.evidence):
            raise ValidationError("provenance evidence item exceeds the maximum length")


@dataclass(frozen=True, slots=True)
class CaptureConsent:
    mode: ConsentMode
    consent_id: str
    reason_code: ConsentReason
    policy_version: str
    granted_at: datetime

    def __post_init__(self) -> None:
        try:
            if not isinstance(self.mode, ConsentMode):
                object.__setattr__(self, "mode", ConsentMode(str(self.mode)))
            if not isinstance(self.reason_code, ConsentReason):
                object.__setattr__(self, "reason_code", ConsentReason(str(self.reason_code)))
        except ValueError as exc:
            raise ValidationError("invalid consent mode or reason") from exc
        for field_name in ("consent_id", "policy_version"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValidationError(f"{field_name} must be non-empty")
            if len(value) > MAX_OPAQUE_ID_LENGTH:
                raise ValidationError(f"{field_name} exceeds the maximum length")
        if not isinstance(self.mode, ConsentMode):
            raise ValidationError("invalid consent mode")
        if not isinstance(self.reason_code, ConsentReason):
            raise ValidationError("invalid consent reason")
        ensure_aware(self.granted_at, "granted_at")


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
