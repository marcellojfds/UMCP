"""Stable, transport-independent domain errors."""


class OMPError(Exception):
    """Base error with a stable machine-readable code."""

    code = "omp_error"

    def __init__(self, message: str = "Open Memory Protocol operation failed") -> None:
        super().__init__(message)
        self.message = message


class ValidationError(OMPError):
    code = "validation_error"


class NotFoundError(OMPError):
    code = "not_found"


class OwnerAccessError(OMPError):
    code = "owner_access_denied"


class InvalidStateTransitionError(OMPError):
    code = "invalid_state_transition"


class VersionConflictError(OMPError):
    code = "version_conflict"


class IdempotencyConflictError(OMPError):
    code = "idempotency_conflict"


class IdempotencyInProgressError(OMPError):
    code = "idempotency_in_progress"


class ImportConflictError(OMPError):
    code = "import_conflict"


class EmbeddingProfileMismatchError(OMPError):
    code = "embedding_profile_mismatch"


class RelationConflictError(OMPError):
    code = "relation_conflict"


class StorageError(OMPError):
    code = "storage_error"


class ConsentRequiredError(OMPError):
    code = "consent_required"


class CaptureDisabledError(OMPError):
    code = "capture_disabled"


class ConnectionRevokedError(OMPError):
    code = "connection_revoked"


class ScopeDeniedError(OMPError):
    code = "scope_denied"


class SpaceForbiddenError(OMPError):
    code = "space_forbidden"


class RestoreBlockedByTombstoneError(OMPError):
    code = "restore_blocked_by_tombstone"
