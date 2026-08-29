"""Cloud HTTP OAuth transport for the UMCP SDK."""

from __future__ import annotations

import json
import time
from collections.abc import Mapping
from typing import Any, cast
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .client import ProtocolError, ToolTransport
from .oauth import OAuthSession, TokenData


class CloudOAuthTransport(ToolTransport):
    """MCP JSON-RPC transport over authenticated Cloud HTTP."""

    def __init__(
        self,
        session: OAuthSession,
        *,
        max_retries: int = 3,
        base_backoff_sec: float = 0.5,
    ) -> None:
        self.session = session
        self.max_retries = max_retries
        self.base_backoff_sec = base_backoff_sec
        self.endpoint = f"{session.base_url}/mcp"
        self._request_id = 0

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def discover(self) -> Mapping[str, Any]:
        """Perform MCP initialize and tools/list discovery."""
        init_res = self._rpc("initialize", {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "umcp-python-sdk", "version": "1.0"},
        })
        tools_res = self._rpc("tools/list", {})
        tools = tools_res.get("result", {}).get("tools", []) or tools_res.get("tools", [])
        return {
            "mcp_protocol_version": init_res.get("result", {}).get("protocolVersion", "2025-03-26"),
            "server_name": init_res.get("result", {}).get("serverInfo", {}).get("name", "umcp-cloud"),
            "server_version": init_res.get("result", {}).get("serverInfo", {}).get("version", "1.0"),
            "tools": [t.get("name") if isinstance(t, dict) else t for t in tools],
            "transport": "cloud_http_oauth",
        }

    def call_tool(self, name: str, arguments: Mapping[str, Any]) -> Mapping[str, Any]:
        """Execute a tool over JSON-RPC 2.0 with safe argument validation and retry policies."""
        # Reject client-supplied authority claims
        if "owner_id" in arguments or "tenant_id" in arguments:
            raise ProtocolError("invalid_argument", "client must not specify owner_id or tenant_id")

        is_safe = (
            name == "memory.search"
            or "idempotency_key" in arguments
        )

        res = self._rpc("tools/call", {"name": name, "arguments": dict(arguments)}, retryable=is_safe)
        return self._unwrap_tool_result(res)

    def _unwrap_tool_result(self, res: dict[str, Any]) -> Mapping[str, Any]:
        if "result" in res:
            res_obj = res["result"]
            is_error = res_obj.get("isError", False)
            content = res_obj.get("content", [])
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_val = item.get("text", "{}")
                    try:
                        parsed = json.loads(text_val)
                        if is_error:
                            return {"ok": False, "error": {"code": "tool_error", "message": str(parsed)}}
                        if isinstance(parsed, dict) and "status" in parsed:
                            if parsed.get("status") == "success":
                                return {"ok": True, "data": parsed.get("data", {})}
                            else:
                                return {"ok": False, "error": parsed.get("error", {"code": "error", "message": "tool execution failed"})}
                        return {"ok": True, "data": parsed}
                    except (json.JSONDecodeError, TypeError):
                        if is_error:
                            return {"ok": False, "error": {"code": "tool_error", "message": text_val}}
                        return {"ok": True, "data": {"raw": text_val}}
            if is_error:
                return {"ok": False, "error": {"code": "tool_error", "message": str(res_obj)}}
            return {"ok": True, "data": res_obj}
        if "error" in res:
            err = res["error"]
            code = str(err.get("code", "mcp_error"))
            msg = str(err.get("message", "unknown error"))
            return {"ok": False, "error": {"code": code, "message": msg}}
        return {"ok": True, "data": res}

    def _rpc(self, method: str, params: dict[str, Any], retryable: bool = False) -> dict[str, Any]:
        req_id = self._next_id()
        payload = json.dumps({
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params,
        }).encode("utf-8")

        attempts = 0
        while True:
            attempts += 1
            token = self.session.get_valid_access_token()
            req = Request(
                self.endpoint,
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                    "Authorization": f"Bearer {token}",
                },
                method="POST",
            )
            try:
                with urlopen(req, timeout=self.session.timeout) as resp:
                    raw = resp.read().decode()
                    if not raw or not raw.strip():
                        return {}
                    try:
                        return json.loads(raw)
                    except json.JSONDecodeError:
                        # Fallback for Server-Sent Events (SSE) stream format
                        for line in raw.splitlines():
                            line_s = line.strip()
                            if line_s.startswith("data:"):
                                try:
                                    return json.loads(line_s[5:].strip())
                                except json.JSONDecodeError:
                                    continue
                        raise ProtocolError("invalid_response", f"Could not decode JSON or SSE response: {raw[:150]}")
            except HTTPError as exc:
                status = exc.code
                if status == 401:
                    # Token might have been revoked or expired on server; try refresh once
                    if attempts == 1 and self.session._tokens and self.session._tokens.refresh_token:
                        try:
                            self.session.refresh()
                            continue
                        except Exception:
                            pass
                    raise ProtocolError("unauthorized", f"Unauthorized: HTTP {status}") from exc
                if status == 403:
                    raise ProtocolError("forbidden", f"Forbidden: HTTP {status}") from exc
                if status in {500, 502, 503, 504} and retryable and attempts < self.max_retries:
                    time.sleep(self.base_backoff_sec * (2 ** (attempts - 1)))
                    continue
                try:
                    err_payload = json.loads(exc.read().decode())
                except Exception:
                    err_payload = {"error": f"HTTP {status}"}
                raise ProtocolError(f"http_{status}", str(err_payload)) from exc
            except (URLError, TimeoutError) as exc:
                if retryable and attempts < self.max_retries:
                    time.sleep(self.base_backoff_sec * (2 ** (attempts - 1)))
                    continue
                raise ProtocolError("network_error", f"Request to {self.endpoint} failed: {exc}") from exc
