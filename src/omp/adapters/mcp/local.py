"""Local file-backed harness for the executable MVP journey.

It is intentionally replaceable: production composition should inject the
domain/application service implemented by the core workstream.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .fakes import InMemoryMemoryService


class PersistentLocalMemoryService(InMemoryMemoryService):
    def __init__(self, path: str | os.PathLike[str]) -> None:
        super().__init__()
        self.path = Path(path)
        self._load()

    def write(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = super().write(payload)
        self._save()
        return result

    def update(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = super().update(payload)
        self._save()
        return result

    def forget(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = super().forget(payload)
        self._save()
        return result

    def import_records(self, records: list[dict[str, Any]]) -> int:
        count = super().import_records(records)
        self._save()
        return count

    def readiness(self) -> bool:
        return True

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict) or payload.get("format") != "omp.local.v0":
                return
            records = payload.get("memories", [])
            if isinstance(records, list):
                super().import_records(records)
        except (OSError, ValueError, TypeError):
            # A corrupt local harness starts empty; import command reports
            # corrupt export files explicitly before calling this service.
            self.records.clear()

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"format": "omp.local.v0", "memories": self.export_records()}
        fd, temporary = tempfile.mkstemp(prefix="omp-local-", suffix=".json", dir=self.path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(
                    payload, handle, sort_keys=True, ensure_ascii=False, separators=(",", ":")
                )
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
        finally:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
