from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from omp.adapters.mcp.adapter import MCPAdapter
from omp.adapters.mcp.fakes import InMemoryMemoryService
from omp.sdk.client import MemoryClient, ProtocolError
from omp.sdk.local import LocalTransport


def _client(service: Any) -> MemoryClient:
    return MemoryClient(LocalTransport(MCPAdapter(service), service))


def _write(client: MemoryClient, key: str = "one") -> dict[str, Any]:
    return client.write(
        content="A synthetic memory for export round trip.",
        type="fact",
        owner_id="owner-a",
        provenance={"source_type": "import", "captured_at": "2026-01-01T00:00:00Z"},
        idempotency_key=key,
    )


def test_export_import_round_trip_and_dry_run(tmp_path: Path) -> None:
    source = InMemoryMemoryService()
    source_client = _client(source)
    _write(source_client)
    package = tmp_path / "export.json"
    document = source_client.export(package)
    payload = json.loads(package.read_text())
    assert document.format == "omp.export.v0"
    assert payload["includes_embeddings"] is False
    assert "embedding" not in payload["memories"][0]

    target = InMemoryMemoryService()
    target_client = _client(target)
    assert target_client.import_file(package, dry_run=True)["count"] == 0
    assert target.records == {}
    assert target_client.import_file(package)["count"] == 1
    assert target_client.import_file(package)["count"] == 0


def test_import_validates_before_commit(tmp_path: Path) -> None:
    source = InMemoryMemoryService()
    source_client = _client(source)
    written = _write(source_client)
    package = tmp_path / "export.json"
    source_client.export(package)
    target = InMemoryMemoryService()
    target_client = _client(target)
    target.records[written["memory"]["id"]] = {**written["memory"], "content": "different"}
    with pytest.raises(ProtocolError) as error:
        target_client.import_file(package)
    assert error.value.code == "version_conflict"
    assert target.records[written["memory"]["id"]]["content"] == "different"


def test_corrupt_and_unknown_export_rejected(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"format": "omp.export.v9", "memories": []}))
    with pytest.raises(ValueError):
        _client(InMemoryMemoryService()).import_file(bad, dry_run=True)
