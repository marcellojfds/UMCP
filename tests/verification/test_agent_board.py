from __future__ import annotations

import json
import subprocess
from pathlib import Path


def run(script: Path, board: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(script), "--board", str(board), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_agent_board_is_idempotent_and_reports_latest(tmp_path: Path) -> None:
    script = Path(__file__).resolve().parents[2] / "scripts" / "agent-board"
    board = tmp_path / "AGENT-BOARD.md"
    event = (
        "publish",
        "--event-id",
        "M01-core-done-abc123",
        "--milestone",
        "M01",
        "--lane",
        "core",
        "--agent",
        "luna-a",
        "--status",
        "DONE",
        "--sha",
        "abc123",
        "--evidence",
        "docs/handoffs/roadmap/M01-CORE-DONE.md",
    )

    first = run(script, board, *event)
    replay = run(script, board, *event)
    shown = run(script, board, "show", "--latest", "--json")

    assert first.returncode == 0
    assert "status=published" in first.stdout
    assert replay.returncode == 0
    assert "status=already-present" in replay.stdout
    assert shown.returncode == 0
    parsed = json.loads(shown.stdout)
    assert parsed[0]["status"] == "DONE"
    assert parsed[0]["sha"] == "abc123"


def test_agent_board_rejects_conflicting_idempotency_key(tmp_path: Path) -> None:
    script = Path(__file__).resolve().parents[2] / "scripts" / "agent-board"
    board = tmp_path / "AGENT-BOARD.md"
    base = (
        "publish",
        "--event-id",
        "dispatch-m01-core",
        "--milestone",
        "M01",
        "--lane",
        "orchestrator",
        "--agent",
        "manager",
        "--status",
        "DISPATCHED",
    )

    assert run(script, board, *base, "--sha", "abc").returncode == 0
    conflict = run(script, board, *base, "--sha", "def")

    assert conflict.returncode == 3
    assert "status=conflict" in conflict.stderr
