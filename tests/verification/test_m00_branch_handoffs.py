from __future__ import annotations

import shutil
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).parents[2]


@contextmanager
def _clean_worktree(tmp_path: Path) -> Iterator[Path]:
    worktree = tmp_path / "clean-repo"
    subprocess.run(
        ["git", "clone", "--no-local", "--quiet", str(ROOT), str(worktree)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "checkout", "--quiet", "-B", "roadmap/integration", "HEAD"],
        cwd=worktree,
        check=True,
        capture_output=True,
        text=True,
    )
    for lane in ("roadmap/luna-core", "roadmap/luna-experience", "roadmap/luna-verification"):
        subprocess.run(
            [
                "git",
                "fetch",
                "--quiet",
                str(ROOT),
                f"refs/heads/{lane}:refs/heads/{lane}",
            ],
            cwd=worktree,
            check=True,
            capture_output=True,
            text=True,
        )
    try:
        yield worktree
    finally:
        shutil.rmtree(worktree)


def _run_audit(worktree: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(worktree / "scripts/assert-m00-branch-handoffs"), *args],
        cwd=worktree,
        capture_output=True,
        text=True,
        check=False,
    )


def _temporary_missing_integration_ref(tmp_path: Path, worktree: Path) -> str:
    ref = f"refs/umcp-test/m00-missing-{tmp_path.name}"
    subprocess.run(
        ["git", "update-ref", ref, "roadmap/luna-verification"],
        cwd=worktree,
        check=True,
    )
    return ref


def test_m00_branch_handoff_audit_reports_integrated_readiness_and_fail_closed_fixture(
    tmp_path: Path,
) -> None:
    with _clean_worktree(tmp_path) as worktree:
        ready = _run_audit(worktree)
        assert ready.returncode == 0
        assert "m00-handoffs=READY" in ready.stdout
        assert "roadmap/luna-core" in ready.stdout

        ref = _temporary_missing_integration_ref(tmp_path, worktree)
        try:
            waiting = _run_audit(worktree, "--integration-ref", ref)
        finally:
            subprocess.run(["git", "update-ref", "-d", ref], cwd=worktree, check=True)

        assert waiting.returncode == 2
        assert "m00-handoffs=WAITING" in waiting.stdout
        assert (
            f"handoff={ref}:docs/handoffs/roadmap/M00-INTEGRATED.md status=missing"
            in waiting.stdout
        )
