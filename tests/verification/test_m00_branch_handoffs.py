from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).parents[2]


def test_m00_branch_handoff_audit_reports_integration_waiting() -> None:
    completed = subprocess.run(
        [str(ROOT / "scripts/assert-m00-branch-handoffs")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 2
    assert "roadmap/luna-core" in completed.stdout
    assert "roadmap/luna-experience" in completed.stdout
    assert "roadmap/luna-verification" in completed.stdout
    assert "roadmap/integration" in completed.stdout
    assert "m00-handoffs=WAITING" in completed.stdout
