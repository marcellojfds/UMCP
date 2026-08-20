"""SDK transport composition for the local MVP."""

from __future__ import annotations

from typing import Any, cast

from omp.adapters.mcp.adapter import MCPAdapter

from .client import InProcessTransport


class LocalTransport(InProcessTransport):
    def __init__(self, adapter: MCPAdapter, service: Any) -> None:
        super().__init__(adapter)
        self.service = service

    def export_records(
        self, *, owner_id: str | None = None, include_embeddings: bool = False
    ) -> list[dict[str, Any]]:
        return cast(
            list[dict[str, Any]],
            self.service.export_records(owner_id=owner_id, include_embeddings=include_embeddings),
        )

    def import_records(self, records: list[dict[str, Any]]) -> int:
        return int(self.service.import_records(records))
