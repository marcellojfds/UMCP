from datetime import UTC, datetime
from uuid import uuid4

import pytest

from omp.domain import (
    InvalidStateTransitionError,
    Memory,
    MemoryState,
    MemoryType,
    ValidationError,
    memory_from_dict,
    memory_to_dict,
)
from tests.fixtures.domain import provenance


def make_memory(**overrides: object) -> Memory:
    values: dict[str, object] = {
        "owner_id": "owner-a",
        "content": "A durable synthetic insight.",
        "memory_type": MemoryType.INSIGHT,
        "importance": 0.8,
        "confidence": 0.7,
        "provenance": provenance(),
        "now": datetime(2026, 1, 2, tzinfo=UTC),
    }
    values.update(overrides)
    return Memory.create(**values)  # type: ignore[arg-type]


def test_memory_round_trip_serialization_preserves_version_and_semantics() -> None:
    memory = make_memory()
    assert memory_from_dict(memory_to_dict(memory)) == memory


@pytest.mark.parametrize("field", ["importance", "confidence"])
@pytest.mark.parametrize("value", [-0.01, 1.01])
def test_probability_bounds_are_enforced(field: str, value: float) -> None:
    with pytest.raises(ValidationError):
        make_memory(**{field: value})


def test_invalid_state_transition_requires_reference() -> None:
    memory = make_memory()
    with pytest.raises(InvalidStateTransitionError):
        memory.evolve(
            now=datetime(2026, 1, 3, tzinfo=UTC),
            state=MemoryState.SUPERSEDED,
        )


def test_lifecycle_allows_archive_and_restore_but_not_resurrection_of_superseded() -> None:
    memory = make_memory()
    archived = memory.evolve(now=datetime(2026, 1, 3, tzinfo=UTC), state=MemoryState.ARCHIVED)
    restored = archived.evolve(now=datetime(2026, 1, 4, tzinfo=UTC), state=MemoryState.ACTIVE)
    superseded = restored.evolve(
        now=datetime(2026, 1, 5, tzinfo=UTC),
        state=MemoryState.SUPERSEDED,
        related_memory_id=uuid4(),
    )
    with pytest.raises(InvalidStateTransitionError):
        superseded.evolve(now=datetime(2026, 1, 6, tzinfo=UTC), state=MemoryState.ACTIVE)


def test_timestamps_must_be_timezone_aware() -> None:
    with pytest.raises(ValidationError):
        make_memory(now=datetime(2026, 1, 2))
