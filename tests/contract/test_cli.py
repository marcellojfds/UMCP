from __future__ import annotations

import json
from pathlib import Path

import pytest

from omp.cli.main import main


def test_cli_json_round_trip(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    data_file = str(tmp_path / "cli.json")
    assert main(["--demo-backend", "status", "--json", "--data-file", data_file]) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["status"] == "ready"

    assert (
        main(
            [
                "--demo-backend",
                "memory",
                "write",
                "--json",
                "--data-file",
                data_file,
                "--owner-id",
                "owner-cli",
                "--type",
                "insight",
                "--content",
                "Synthetic CLI memory.",
                "--idempotency-key",
                "cli-write",
            ]
        )
        == 0
    )
    written = json.loads(capsys.readouterr().out)
    memory_id = written["memory"]["id"]
    assert (
        main(
            [
                "--demo-backend",
                "memory",
                "search",
                "--json",
                "--data-file",
                data_file,
                "--owner-id",
                "owner-cli",
                "--query",
                "Synthetic CLI",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["count"] == 1

    export_path = tmp_path / "cli-export.json"
    assert (
        main(["--demo-backend", "export", "--json", "--data-file", data_file, str(export_path)])
        == 0
    )
    assert json.loads(capsys.readouterr().out)["format"] == "omp.export.v0"
    assert (
        main(
            [
                "--demo-backend",
                "import",
                "--json",
                "--data-file",
                str(tmp_path / "other.json"),
                "--dry-run",
                str(export_path),
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["status"] == "validated"
    assert memory_id
