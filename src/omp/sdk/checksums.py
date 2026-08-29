"""Versioned checksum calculation utilities for canonical payloads and report verification."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def compute_canonical_checksum(payload: dict[str, Any]) -> str:
    """Compute deterministic SHA-256 digest of canonical JSON serialization.

    The 'checksum' field itself is excluded from the calculation to ensure self-consistency.
    """
    clean_payload = {k: v for k, v in payload.items() if k != "checksum"}
    canonical_bytes = json.dumps(clean_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{hashlib.sha256(canonical_bytes).hexdigest()}"


def compute_file_sha256(file_path: Path | str) -> str:
    """Compute SHA-256 hash of a file on disk."""
    p = Path(file_path)
    content = p.read_bytes()
    return f"sha256:{hashlib.sha256(content).hexdigest()}"
