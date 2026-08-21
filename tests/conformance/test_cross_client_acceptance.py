from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]
DEMOS = {
    "local-integration": ROOT / "scripts/demo-local-integration",
    "cross-client": ROOT / "scripts/demo-cross-client-memory",
    "memory-inbox": ROOT / "scripts/demo-memory-inbox",
    "concepts-and-notes": ROOT / "scripts/demo-concepts-and-notes",
    "backup-delete-restore": ROOT / "scripts/demo-backup-delete-restore",
}


@pytest.mark.parametrize("scenario", tuple(DEMOS))
def test_verification_fixture_demo_is_black_box_and_fail_closed(scenario: str) -> None:
    completed = subprocess.run(
        [str(DEMOS[scenario])],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "synthetic-run=" in completed.stdout
    assert "No meu projeto" not in completed.stdout


def test_cross_client_acceptance_exercises_required_contract() -> None:
    completed = subprocess.run(
        [str(DEMOS["cross-client"])],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    # The fixture's assertions cover candidate -> confirm -> Claude recall,
    # provenance/source/space, tenant-B zero, revocation, Claude continuity,
    # forget and tombstone-safe restore. The demo intentionally prints no data.
