"""Static contract for the container's hosted HTTP entrypoint."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parents[2]


def test_container_uses_hosted_http_not_synthetic_m1() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    entrypoint = (ROOT / "src/omp/server/__main__.py").read_text(encoding="utf-8")
    official = (ROOT / "src/omp/server/official.py").read_text(encoding="utf-8")

    assert '"--cloud-http"' in dockerfile
    assert '"--m1-http"' not in dockerfile
    assert "create_fail_closed_cloud_http_app()" in entrypoint
    assert "return create_cloud_http_app(" in official
    assert "redirect_slashes=False" in official
