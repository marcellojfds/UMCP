"""Low-cardinality structured logging for MCP boundaries."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Mapping

ALLOWED_FIELDS = frozenset(
    {
        "event",
        "request_id",
        "tool",
        "status",
        "duration_ms",
        "protocol_version",
        "error_code",
        "result_count",
        "transport",
    }
)


class StructuredLogger:
    """Allowlist-only logger; payloads and raw object IDs are never accepted."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.logger = logger or logging.getLogger("omp.mcp")

    def emit(self, **fields: object) -> None:
        safe = {key: value for key, value in fields.items() if key in ALLOWED_FIELDS}
        self.logger.info(json.dumps(safe, sort_keys=True, separators=(",", ":")))


def duration_bucket(start: float) -> int:
    elapsed = max(0, int((time.monotonic() - start) * 1000))
    if elapsed < 10:
        return 10
    if elapsed < 50:
        return 50
    if elapsed < 100:
        return 100
    if elapsed < 500:
        return 500
    if elapsed < 1_000:
        return 1_000
    return 5_000


def json_log_fields(record: Mapping[str, object]) -> dict[str, object]:
    """Useful in tests to assert that an emitted record is allowlist-only."""

    return {key: record[key] for key in record if key in ALLOWED_FIELDS}
