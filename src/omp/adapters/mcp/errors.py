"""Stable public errors and intentionally opaque error mapping."""

from __future__ import annotations

from enum import StrEnum


class PublicErrorCode(StrEnum):
    VALIDATION = "validation_error"
    NOT_FOUND = "not_found"
    VERSION_CONFLICT = "version_conflict"
    FORBIDDEN = "forbidden"
    RATE_LIMITED = "rate_limited"
    DEPENDENCY_UNAVAILABLE = "dependency_unavailable"
    INTERNAL = "internal_error"


class PublicError(Exception):
    """Error safe to expose at the protocol boundary."""

    def __init__(self, code: PublicErrorCode, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


class NotFoundError(Exception):
    pass


class VersionConflictError(Exception):
    pass


class ForbiddenError(Exception):
    pass


class RateLimitedError(Exception):
    pass


def map_service_error(error: BaseException) -> PublicError:
    """Map known application errors without exposing their text or identity."""

    if isinstance(error, PublicError):
        return error
    service_code = getattr(error, "code", None)
    if service_code == "validation_error" or error.__class__.__name__ in {
        "ValidationError",
        "InvalidStateTransitionError",
        "IdempotencyConflictError",
    }:
        return PublicError(PublicErrorCode.VALIDATION, "invalid memory operation")
    if service_code in {"owner_access_denied", "forbidden"} or error.__class__.__name__ in {
        "OwnerAccessError",
        "Forbidden",
    }:
        return PublicError(PublicErrorCode.FORBIDDEN, "operation not permitted")
    if isinstance(error, NotFoundError) or error.__class__.__name__ in {
        "MemoryNotFound",
        "NotFound",
        "NotFoundError",
    }:
        return PublicError(PublicErrorCode.NOT_FOUND, "memory not found")
    if (
        service_code == "version_conflict"
        or isinstance(error, VersionConflictError)
        or error.__class__.__name__
        in {
            "VersionConflict",
            "VersionConflictError",
            "OptimisticConcurrencyError",
        }
    ):
        return PublicError(PublicErrorCode.VERSION_CONFLICT, "memory version conflict")
    if isinstance(error, ForbiddenError) or error.__class__.__name__ in {
        "Forbidden",
        "OwnerMismatch",
    }:
        return PublicError(PublicErrorCode.FORBIDDEN, "operation not permitted")
    if isinstance(error, RateLimitedError):
        return PublicError(PublicErrorCode.RATE_LIMITED, "rate limit exceeded", retryable=True)
    if isinstance(error, TimeoutError | ConnectionError) or error.__class__.__name__ in {
        "DependencyUnavailable",
        "ServiceUnavailable",
    }:
        return PublicError(
            PublicErrorCode.DEPENDENCY_UNAVAILABLE, "dependency unavailable", retryable=True
        )
    return PublicError(PublicErrorCode.INTERNAL, "internal error")
