from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import subprocess
import sys
import time
from io import StringIO
from pathlib import Path
from typing import Any

import pytest

from omp.adapters.mcp.adapter import MCPAdapter
from omp.adapters.mcp.fakes import InMemoryMemoryService
from omp.adapters.mcp.observability import StructuredLogger
from omp.adapters.mcp.transport import create_health_app
from omp.config import OMPSettings
from omp.server.composition import create_runtime


def _write(canary: str, **extra: Any) -> dict[str, Any]:
    value = {
        "content": canary,
        "type": "fact",
        "owner_id": "owner-CANARY-PII-LOCAL",
        "provenance": {"source_type": "import", "captured_at": "2026-01-01T00:00:00Z"},
        "idempotency_key": "CANARY-SECRET-LOCAL",
    }
    value.update(extra)
    return value


def test_canary_secret_and_pii_do_not_reach_logs_traces_or_errors(tmp_path: Path) -> None:
    canary = "CANARY-CONTENT-LOCAL-7f9a"
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    logger = logging.getLogger("test-privacy-output")
    logger.handlers[:] = [handler]
    logger.setLevel(logging.INFO)
    adapter = MCPAdapter(InMemoryMemoryService(), logger=StructuredLogger(logger))
    result = asyncio.run(adapter.call_tool("memory.write", _write(canary)))
    assert result["ok"] is True

    class LeakingService(InMemoryMemoryService):
        def search(self, payload: dict[str, Any]) -> list[Any]:
            raise RuntimeError(f"SELECT secret FROM memories: {payload['query']}")

    error = asyncio.run(
        MCPAdapter(LeakingService(), logger=StructuredLogger(logger)).call_tool(
            "memory.search", {"query": canary, "owner_id": "owner-CANARY-PII-LOCAL"}
        )
    )
    combined = stream.getvalue() + json.dumps(error)
    assert error["error"]["code"] == "internal_error"
    assert "SELECT" not in combined
    assert "Traceback" not in combined
    assert canary not in combined
    assert "CANARY-PII-LOCAL" not in combined
    assert "CANARY-SECRET-LOCAL" not in combined

    # Alpha has no tracing exporter. This synthetic trace capture documents the
    # required boundary: only the already-sanitized log fields may be emitted.
    trace_path = tmp_path / "trace.json"
    trace_path.write_text(json.dumps({"attributes": {"event": "mcp_request", "status": "ok"}}))
    output_path = tmp_path / "stderr.log"
    output_path.write_text(stream.getvalue())
    scan = subprocess.run(
        [str(Path(__file__).parents[2] / "scripts" / "scan-runtime-output"), str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert scan.returncode == 0, scan.stderr


def test_timeout_is_single_attempt_without_retry_storm() -> None:
    class SlowService(InMemoryMemoryService):
        calls = 0

        async def search(self, payload: dict[str, Any]) -> list[Any]:
            self.calls += 1
            await asyncio.sleep(0.05)
            return []

    service = SlowService()
    result = asyncio.run(
        MCPAdapter(service).call_tool(
            "memory.search", {"query": "synthetic", "owner_id": "owner-a", "timeout_ms": 1}
        )
    )
    assert result["error"] == {
        "code": "dependency_unavailable",
        "message": "dependency unavailable",
        "retryable": True,
    }
    assert service.calls == 1


def test_readiness_fails_closed_and_default_runtime_never_selects_demo() -> None:
    runtime = create_runtime(
        OMPSettings(database_url="postgresql+asyncpg://127.0.0.1:1/omp", migration_head="head")
    )
    assert runtime.backend == "postgres"
    assert asyncio.run(runtime.readiness()) is False
    with pytest.raises(RuntimeError, match="readiness"):
        asyncio.run(runtime.startup())
    asyncio.run(runtime.close())


def test_liveness_is_independent_but_readiness_hides_dependency_details() -> None:
    from fastapi.testclient import TestClient

    app = create_health_app(MCPAdapter(InMemoryMemoryService()), readiness=lambda: False)
    client = TestClient(app)
    assert client.get("/healthz").json() == {"status": "ok"}
    response = client.get("/readyz")
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}


@pytest.mark.skipif(os.name == "nt", reason="SIGTERM is a POSIX lifecycle contract")
def test_server_accepts_sigterm_without_demo_fallback(tmp_path: Path) -> None:
    environment = dict(os.environ)
    root = Path(__file__).parents[2]
    environment.update({"PYTHONPATH": str(root / "src"), "OMP_BACKEND": "demo"})
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "omp.server",
            "--demo-backend",
            "--data-file",
            str(tmp_path / "x.json"),
        ],
        cwd=root,
        env=environment,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        time.sleep(0.25)
        process.send_signal(signal.SIGTERM)
        _, stderr = process.communicate(timeout=5)
    finally:
        if process.poll() is None:
            process.kill()
    assert process.returncode is not None
    assert "CANARY-" not in stderr
