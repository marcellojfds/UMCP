from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).parents[2]


def run_script(name: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(ROOT / "scripts" / name), *args], cwd=ROOT, capture_output=True, text=True, check=False
    )


def test_worktree_context_control_passes_for_lane() -> None:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    completed = run_script("assert-worktree-context", "--expected-head", head)
    assert completed.returncode == 0, completed.stderr
    assert "branch=roadmap/luna-verification" in completed.stdout


def test_stagnation_detector_distinguishes_healthy_and_triggered_logs(tmp_path: Path) -> None:
    healthy = {
        "consecutive_same_blocker": 0,
        "incremental_changes_since_acceptance": 2,
        "subsystem_switches_without_demo": 1,
        "repeated_gates_without_hypothesis_change": False,
        "handoff_has_acceptance_command": True,
        "context_reopens_without_next_action": 0,
    }
    healthy_path = tmp_path / "healthy.json"
    healthy_path.write_text(json.dumps(healthy), encoding="utf-8")
    assert run_script("detect-stagnation", str(healthy_path)).returncode == 0

    blocked = {**healthy, "consecutive_same_blocker": 3}
    blocked_path = tmp_path / "blocked.json"
    blocked_path.write_text(json.dumps(blocked), encoding="utf-8")
    completed = run_script("detect-stagnation", str(blocked_path))
    assert completed.returncode == 1
    assert "three_same_blockers" in completed.stdout


def test_gate_freshness_manifest_is_machine_checkable() -> None:
    manifest = ROOT / "docs/handoffs/roadmap/GATE-FRESHNESS.json"
    completed = run_script("check-gate-freshness", str(manifest), "--markdown")
    assert completed.returncode == 0, completed.stderr
    assert "| Gate | SHA | Freshness | Result | Artifact |" in completed.stdout
    assert "environment-blocked" in completed.stdout


def test_capability_report_records_prohibitions_and_environment_classification() -> None:
    report = ROOT / "docs/handoffs/roadmap/capability-preflight.json"
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["prohibition_check"] == {
        "external_services": "not-used",
        "holdout": "not-run",
        "real_data": "not-used",
    }
    names = {check["name"]: check["status"] for check in payload["checks"]}
    assert names["browser-automation"] == "not-run"
