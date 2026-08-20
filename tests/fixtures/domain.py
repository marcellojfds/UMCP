"""Canonical synthetic fixtures shared by core tests."""

from datetime import UTC, datetime

from omp.domain import MemoryType, Provenance, SourceType


def provenance(source_id: str = "fixture-study") -> Provenance:
    return Provenance(
        source_type=SourceType.CONVERSATION,
        source_id=source_id,
        source_model="fixture-agent",
        captured_at=datetime(2026, 1, 1, tzinfo=UTC),
        evidence=("synthetic fixture",),
    )


CANONICAL_MEMORY = {
    "owner_id": "owner-a",
    "content": (
        "Marketplaces with local network effects should build geographic density before expansion."
    ),
    "memory_type": MemoryType.INSIGHT,
    "importance": 0.9,
    "confidence": 0.85,
    "provenance": provenance(),
    "space": "mba",
    "idempotency_key": "fixture-market-density-v1",
}
