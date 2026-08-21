from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).parents[2]


def test_integration_readiness_fails_closed_until_m00_integrated_exists() -> None:
    completed = subprocess.run(
        [str(ROOT / "scripts/assert-roadmap-integration-ready"), "--milestone", "M00"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 2
    assert "sync=WAITING" in completed.stdout
    assert "M00-INTEGRATED.md" in completed.stdout
