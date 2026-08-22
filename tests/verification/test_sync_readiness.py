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
    try:
        yield worktree
    finally:
        shutil.rmtree(worktree)


def _run_readiness(worktree: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            str(worktree / "scripts/assert-roadmap-integration-ready"),
            "--milestone",
            "M00",
            *args,
        ],
        cwd=worktree,
        capture_output=True,
        text=True,
        check=False,
    )


def test_integration_readiness_is_ready_and_remains_fail_closed_for_missing_fixture(
    tmp_path: Path,
) -> None:
    with _clean_worktree(tmp_path) as worktree:
        ready = _run_readiness(worktree)
        assert ready.returncode == 0
        assert "sync=READY milestone=M00 ref=roadmap/integration" in ready.stdout
        assert "M00-INTEGRATED.md" in ready.stdout

        ref = f"refs/umcp-test/m00-readiness-missing-{tmp_path.name}"
        subprocess.run(
            [
                "git",
                "update-ref",
                ref,
                "refs/remotes/origin/roadmap/luna-verification",
            ],
            cwd=worktree,
            check=True,
        )
        try:
            waiting = _run_readiness(worktree, "--integration-ref", ref)
        finally:
            subprocess.run(["git", "update-ref", "-d", ref], cwd=worktree, check=True)

        assert waiting.returncode == 2
        assert f"sync=WAITING milestone=M00 ref={ref}" in waiting.stdout
        assert "missing=docs/handoffs/roadmap/M00-INTEGRATED.md" in waiting.stdout
