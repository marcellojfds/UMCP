from __future__ import annotations

import pytest

from tests.fixtures.m1_http import run_m1_acceptance


@pytest.mark.asyncio
async def test_m1_portable_memory_acceptance_journey_over_http() -> None:
    """Exercise capture -> inbox -> recall -> isolation -> revoke -> tombstone restore."""
    report = await run_m1_acceptance()
    assert report.counts == {
        "candidate": 1,
        "recall": 1,
        "tenant_b": 0,
        "forgotten": 1,
        "restored": 0,
    }
