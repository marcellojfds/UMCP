"""SDK transport and typed convenience methods; no business rules live here."""

from __future__ import annotations

import json
import subprocess
import sys
import uuid
from collections.abc import AsyncIterator, Mapping, Sequence
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol, cast

import anyio
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from .export import ExportDocument, load_export, write_export


class ProtocolError(RuntimeError):
    def __init__(
        self, code: str, message: str, *, request_id: str | None = None, retryable: bool = False
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.request_id = request_id
        self.retryable = retryable


class ToolTransport(Protocol):
    def call_tool(self, name: str, arguments: Mapping[str, Any]) -> Mapping[str, Any]: ...


class InProcessTransport:
    def __init__(self, adapter: Any) -> None:
        self.adapter = adapter

    def call_tool(self, name: str, arguments: Mapping[str, Any]) -> Mapping[str, Any]:
        return cast(
            Mapping[str, Any],
            self.adapter.call_tool_sync(name, arguments, request_id="sdk_" + uuid.uuid4().hex),
        )


class HTTPTransport:
    def __init__(self, endpoint: str, *, timeout: float = 5.0) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout

    def call_tool(self, name: str, arguments: Mapping[str, Any]) -> Mapping[str, Any]:
        raise ProtocolError(
            "dependency_unavailable",
            "HTTP MCP transport is not supported in Alpha v0; use stdio",
        )


class StdioTransport:
    """Official MCP ``ClientSession`` transport over a fresh stdio process."""

    def __init__(
        self,
        command: Sequence[str] | None = None,
        *,
        data_file: str | None = None,
        demo_backend: bool = False,
        env: Mapping[str, str] | None = None,
        log_path: str | Path | None = None,
    ) -> None:
        self.command = list(command or [sys.executable, "-m", "omp.server"])
        self.data_file = data_file
        self.demo_backend = demo_backend
        self.env = dict(env) if env is not None else None
        self.log_path = Path(log_path) if log_path is not None else None
        self.backend = (
            "demo" if demo_backend or (self.env or {}).get("OMP_BACKEND") == "demo" else "postgres"
        )

    def call_tool(self, name: str, arguments: Mapping[str, Any]) -> Mapping[str, Any]:
        try:
            return anyio.run(self._call_async, name, dict(arguments))
        except BaseException:
            raise ProtocolError(
                "dependency_unavailable",
                "MCP server unavailable",
                retryable=True,
            ) from None

    async def _call_async(self, name: str, arguments: dict[str, Any]) -> Mapping[str, Any]:
        async with self._session() as session:
            await session.initialize()
            result = await session.call_tool(name, arguments)
            return _result_payload(result)

    async def _discover_async(self) -> Mapping[str, Any]:
        async with self._session() as session:
            initialized = await session.initialize()
            tools = await session.list_tools()
            return {
                "mcp_protocol_version": initialized.protocolVersion,
                "server_name": initialized.serverInfo.name,
                "server_version": initialized.serverInfo.version,
                "tools": [tool.name for tool in tools.tools],
                "transport": "stdio",
            }

    def discover(self) -> Mapping[str, Any]:
        try:
            return anyio.run(self._discover_async)
        except BaseException:
            raise ProtocolError(
                "dependency_unavailable",
                "MCP server unavailable",
                retryable=True,
            ) from None

    def _session(self) -> Any:
        command, args = self._server_command()
        parameters = StdioServerParameters(command=command, args=args, env=self.env)
        return _stdio_session(parameters, self.log_path)

    def _server_command(self) -> tuple[str, list[str]]:
        command = list(self.command)
        args = command[1:]
        if self.demo_backend:
            args.append("--demo-backend")
        if self.data_file:
            args.extend(["--data-file", self.data_file])
        return command[0], args

    def export_records(
        self, *, owner_id: str | None = None, include_embeddings: bool = False
    ) -> list[dict[str, Any]]:
        if self.backend != "demo" and not owner_id:
            raise ProtocolError("validation_error", "owner_id is required for Postgres export")
        command, args = self._server_command()
        args.extend(["--admin-export"])
        if owner_id:
            args.extend(["--owner-id", owner_id])
        if include_embeddings:
            args.append("--include-embeddings")
        result = subprocess.run(
            [command, *args],
            env=self.env,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            raise _admin_error(result.stdout, "export could not be completed")
        try:
            payload = json.loads(result.stdout)
            records = payload["records"]
            if not isinstance(records, list):
                raise ValueError
            return records
        except (ValueError, TypeError, KeyError, json.JSONDecodeError):
            raise ProtocolError("internal_error", "export response was invalid") from None

    def import_records(self, records: list[dict[str, Any]]) -> int:
        command, args = self._server_command()
        args.extend(["--admin-import", "-"])
        result = subprocess.run(
            [command, *args],
            input=json.dumps(
                {
                    "format": "omp.export.v0",
                    "exported_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                    "includes_embeddings": any(
                        item.get("embedding_values") is not None for item in records
                    ),
                    "memories": records,
                },
                ensure_ascii=False,
            ),
            env=self.env,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            raise _admin_error(result.stdout, "import could not be completed")
        try:
            payload = json.loads(result.stdout)
            value = payload["imported"] if "imported" in payload else payload["count"]
            return int(value)
        except (ValueError, TypeError, KeyError, json.JSONDecodeError):
            raise ProtocolError("internal_error", "import response was invalid") from None


class OfficialStdioTransport(StdioTransport):
    """Descriptive alias for callers requiring the official SDK path."""


@asynccontextmanager
async def _stdio_session(
    parameters: StdioServerParameters, log_path: Path | None = None
) -> AsyncIterator[ClientSession]:
    if log_path is None:
        async with stdio_client(parameters) as streams:
            async with ClientSession(*streams) as session:
                yield session
        return
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as log_file:
        async with stdio_client(parameters, errlog=log_file) as streams:
            async with ClientSession(*streams) as session:
                yield session


def _result_payload(result: Any) -> Mapping[str, Any]:
    structured = getattr(result, "structuredContent", None)
    if structured is not None:
        return cast(Mapping[str, Any], structured)
    for content in getattr(result, "content", []):
        text = getattr(content, "text", None)
        if text is not None:
            return cast(Mapping[str, Any], json.loads(text))
    raise ProtocolError("dependency_unavailable", "MCP tool response was empty")


def _admin_error(output: str, fallback: str) -> ProtocolError:
    try:
        payload = json.loads(output)
        error = payload.get("error", {})
        code = str(error.get("code", "internal_error"))
        message = str(error.get("message", fallback))
        return ProtocolError(code, message)
    except (TypeError, ValueError, json.JSONDecodeError):
        return ProtocolError("internal_error", fallback)


class MemoryClient:
    def __init__(self, transport: ToolTransport) -> None:
        self.transport = transport

    def capabilities(self) -> Mapping[str, Any]:
        if hasattr(self.transport, "adapter"):
            return cast(Mapping[str, Any], cast(Any, self.transport).adapter.capabilities())
        discover = getattr(self.transport, "discover", None)
        if discover is not None:
            result = dict(discover())
            result.update(
                {
                    "protocol_version": "omp.mcp.v0",
                    "request_id": "sdk_" + uuid.uuid4().hex,
                    "backend": getattr(self.transport, "backend", "unknown"),
                }
            )
            return result
        raise ProtocolError("dependency_unavailable", "capability discovery unavailable")

    def _call(self, name: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
        envelope = dict(self.transport.call_tool(name, arguments))
        if envelope.get("ok") is True:
            return dict(envelope.get("data", {}))
        error = envelope.get("error", {})
        raise ProtocolError(
            str(error.get("code", "internal_error")),
            str(error.get("message", "internal error")),
            request_id=envelope.get("request_id"),
            retryable=bool(error.get("retryable", False)),
        )

    def write(self, **arguments: Any) -> dict[str, Any]:
        return self._call("memory.write", arguments)

    def search(self, **arguments: Any) -> dict[str, Any]:
        return self._call("memory.search", arguments)

    def update(self, **arguments: Any) -> dict[str, Any]:
        return self._call("memory.update", arguments)

    def forget(self, **arguments: Any) -> dict[str, Any]:
        return self._call("memory.forget", arguments)

    def export(
        self, path: str | Path, *, owner_id: str | None = None, include_embeddings: bool = False
    ) -> ExportDocument:
        exporter = getattr(self.transport, "export_records", None)
        if not callable(exporter):
            raise ProtocolError("dependency_unavailable", "export requires a local/admin transport")
        return write_export(
            path,
            cast(
                list[dict[str, Any]],
                exporter(owner_id=owner_id, include_embeddings=include_embeddings),
            ),
            include_embeddings=include_embeddings,
        )

    def import_file(self, path: str | Path, *, dry_run: bool = False) -> dict[str, Any]:
        document = load_export(path)
        importer = getattr(self.transport, "import_records", None)
        if not callable(importer) and not dry_run:
            raise ProtocolError("dependency_unavailable", "import requires a local/admin transport")
        if dry_run:
            count = 0
        else:
            try:
                if not callable(importer):
                    raise ProtocolError(
                        "dependency_unavailable", "import requires a local/admin transport"
                    )
                count = int(
                    importer(
                        [
                            item.model_dump(mode="json", exclude_none=True)
                            for item in document.memories
                        ]
                    )
                )
            except ProtocolError:
                raise
            except Exception as exc:
                code = (
                    "version_conflict"
                    if exc.__class__.__name__ in {"VersionConflict", "VersionConflictError"}
                    else "internal_error"
                )
                raise ProtocolError(code, "import could not be applied") from None
        return {
            "status": "validated" if dry_run else "imported",
            "count": count,
            "format": document.format,
        }


MCPClient = MemoryClient
