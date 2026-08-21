"""Local-only administrative API with passwordless session semantics."""

from __future__ import annotations

import hashlib
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, Response
from mcp.server.auth.provider import AccessToken
from pydantic import BaseModel, ConfigDict, Field

from omp.cloud.security import Principal, Scope
from omp.cloud.tenant import tenant_scope


class _Request(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MagicLinkRequest(_Request):
    email: str = Field(min_length=3, max_length=320)
    redirect: str = "/"


class MemoryWriteRequest(_Request):
    content: str = Field(min_length=1, max_length=16_384)
    type: str
    provenance: dict[str, object]
    idempotency_key: str = Field(min_length=1, max_length=128)
    importance: float = Field(default=0.5, ge=0, le=1)
    confidence: float = Field(default=0.5, ge=0, le=1)


class MemoryUpdateRequest(_Request):
    expected_version: int = Field(ge=1)
    patch: dict[str, object]
    idempotency_key: str = Field(min_length=1, max_length=128)


class ConnectionRequest(_Request):
    name: str = Field(min_length=1, max_length=128)
    scopes: set[Scope] = Field(min_length=1)


class AgentCredentialRequest(_Request):
    name: str = Field(min_length=1, max_length=128)
    scopes: set[Scope] = Field(min_length=1)
    expires_in_seconds: int = Field(default=3600, ge=60, le=86_400)


@dataclass(slots=True)
class _MagicLink:
    digest: str
    principal: Principal
    expires_at: datetime
    used: bool = False


class LocalMailboxAuth:
    """Development mailbox sink; tokens are single-use and only token digests persist."""

    def __init__(
        self,
        *,
        secure_cookies: bool = False,
        magic_link_limit: int = 5,
        magic_link_window: timedelta = timedelta(minutes=15),
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if magic_link_limit < 1 or magic_link_window <= timedelta(0):
            raise ValueError("magic-link rate limit must be positive")
        self.secure_cookies = secure_cookies
        self._magic_link_limit = magic_link_limit
        self._magic_link_window = magic_link_window
        self._clock = clock or (lambda: datetime.now(UTC))
        self.outbox: list[dict[str, str]] = []
        self._links: dict[str, _MagicLink] = {}
        self._sessions: dict[str, Principal] = {}
        self._csrf: dict[str, str] = {}
        self._connections: dict[str, dict[str, object]] = {}
        self._agent_credentials: dict[str, dict[str, object]] = {}
        self._agent_token_index: dict[str, str] = {}
        self._operations: dict[str, dict[str, object]] = {}
        self._magic_link_attempts: dict[str, list[datetime]] = {}

    def request(self, email: str) -> bool:
        # Non-enumerating response. A deterministic local principal makes the
        # development integration usable without storing real identities.
        now = self._clock()
        email_digest = hashlib.sha256(email.strip().casefold().encode()).hexdigest()
        previous = self._magic_link_attempts.get(email_digest, [])
        allowed = [item for item in previous if item > now - self._magic_link_window]
        if len(allowed) >= self._magic_link_limit:
            self._magic_link_attempts[email_digest] = allowed
            return False
        allowed.append(now)
        self._magic_link_attempts[email_digest] = allowed
        principal = Principal(
            subject_id=uuid4(),
            tenant_id=uuid4(),
            membership_id=uuid4(),
            credential_id=uuid4(),
            scopes=frozenset(Scope),
            auth_method="local-magic-link",
            expires_at=now + timedelta(hours=1),
        )
        raw = secrets.token_urlsafe(32)
        digest = hashlib.sha256(raw.encode()).hexdigest()
        self._links[digest] = _MagicLink(
            digest, principal, now + timedelta(minutes=10)
        )
        self.outbox.append({"to": "captured", "token": raw})
        return True

    def consume(self, raw: str) -> tuple[str, str] | None:
        link = self._links.get(hashlib.sha256(raw.encode()).hexdigest())
        if link is None or link.used or link.expires_at <= self._clock():
            return None
        link.used = True
        session, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(24)
        self._sessions[hashlib.sha256(session.encode()).hexdigest()] = link.principal
        self._csrf[hashlib.sha256(session.encode()).hexdigest()] = csrf
        return session, csrf

    def session(self, raw: str | None) -> Principal | None:
        return self._sessions.get(hashlib.sha256(raw.encode()).hexdigest()) if raw else None

    def csrf(self, raw: str | None) -> str | None:
        return self._csrf.get(hashlib.sha256(raw.encode()).hexdigest()) if raw else None

    def logout(self, raw: str | None) -> None:
        if raw:
            digest = hashlib.sha256(raw.encode()).hexdigest()
            self._sessions.pop(digest, None)
            self._csrf.pop(digest, None)

    @staticmethod
    def _receipt(kind: str, principal: Principal, status: str) -> dict[str, object]:
        return {
            "id": "op_" + secrets.token_urlsafe(12),
            "kind": kind,
            "status": status,
            "tenant_id": str(principal.tenant_id),
            "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        }

    def receipt(self, kind: str, principal: Principal, status: str) -> dict[str, object]:
        value = self._receipt(kind, principal, status)
        self._operations[str(value["id"])] = value
        return value


class LocalAgentCredentialVerifier:
    """Verify local-development PATs without retaining their raw values.

    This adapter intentionally shares only the official MCP token-verifier
    boundary. It is not an OIDC replacement: a production verifier must fetch
    and validate tokens from its configured identity provider.
    """

    def __init__(self, auth: LocalMailboxAuth, *, issuer: str, audience: str) -> None:
        self._auth = auth
        self._issuer = issuer
        self._audience = audience

    async def verify_token(self, token: str) -> AccessToken | None:
        digest = hashlib.sha256(token.encode()).hexdigest()
        credential_id = self._auth._agent_token_index.get(digest)
        if credential_id is None:
            return None
        credential = self._auth._agent_credentials.get(credential_id)
        if credential is None or credential.get("_token_digest") != digest:
            return None
        try:
            expires_at = datetime.fromisoformat(str(credential["expires_at"]))
            scopes = [Scope(str(item)).value for item in cast(list[object], credential["scopes"])]
            if bool(credential["revoked"]) or expires_at <= datetime.now(UTC):
                return None
            subject_id = str(credential["_subject_id"])
            tenant_id = str(credential["tenant_id"])
            membership_id = str(credential["_membership_id"])
            internal_credential_id = str(credential["_credential_id"])
        except (KeyError, TypeError, ValueError):
            return None
        return AccessToken(
            token=token,
            client_id=f"local-agent:{credential_id}",
            scopes=scopes,
            expires_at=int(expires_at.timestamp()),
            resource=self._audience,
            subject=subject_id,
            claims={
                "iss": self._issuer,
                "tenant_id": tenant_id,
                "membership_id": membership_id,
                "credential_id": internal_credential_id,
            },
        )


def create_admin_app(auth: LocalMailboxAuth, runtime: object | None = None) -> FastAPI:
    app = FastAPI(title="UMCP Admin API", docs_url=None, redoc_url=None)

    def principal(request: Request) -> Principal:
        value = auth.session(request.cookies.get("umcp_session"))
        if value is None:
            raise HTTPException(status_code=401, detail="authentication required")
        return value

    def require_csrf(request: Request) -> Principal:
        value = principal(request)
        if not secrets.compare_digest(
            request.headers.get("x-umcp-csrf", ""),
            auth.csrf(request.cookies.get("umcp_session")) or "",
        ):
            raise HTTPException(status_code=403, detail="request rejected")
        return value

    def owner(value: Principal) -> str:
        return f"cloud:{value.tenant_id}:{value.subject_id}"

    async def call(value: Principal, name: str, payload: dict[str, object]) -> dict[str, object]:
        if runtime is None or not hasattr(runtime, "adapter"):
            raise HTTPException(status_code=503, detail="service unavailable")
        payload["owner_id"] = owner(value)
        with tenant_scope(value.tenant_id):
            result = await runtime.adapter.call_tool(name, payload)
        if not result.get("ok"):
            code = result["error"]["code"]
            status = 404 if code == "not_found" else 409 if code == "version_conflict" else 400
            raise HTTPException(status_code=status, detail="request could not be completed")
        data = cast(dict[str, object], result["data"])
        _redact_owner(data)
        return data

    @app.get("/api/capabilities")
    async def capabilities() -> dict[str, object]:
        return {
            "version": "umcp.admin.v1",
            "auth": "local_magic_link",
            "email_delivery": "captured",
            "connections": True,
            "agent_credentials": True,
            "tenant_export": True,
            "account_deletion": True,
        }

    @app.post("/api/auth/magic-link")
    async def magic_link(payload: MagicLinkRequest) -> dict[str, str]:
        if payload.redirect not in {"/", "/dashboard", "/memories"}:
            raise HTTPException(status_code=400, detail="invalid request")
        auth.request(payload.email)
        return {"status": "accepted"}

    @app.get("/api/auth/callback")
    async def callback(token: str, response: Response) -> dict[str, str]:
        issued = auth.consume(token)
        if issued is None:
            raise HTTPException(status_code=400, detail="invalid or expired link")
        session, csrf = issued
        response.set_cookie(
            "umcp_session",
            session,
            httponly=True,
            secure=auth.secure_cookies,
            samesite="lax",
            path="/",
        )
        return {"status": "authenticated", "csrf": csrf}

    @app.get("/api/session")
    async def session(request: Request) -> dict[str, object]:
        value = principal(request)
        return {
            "subject_id": str(value.subject_id),
            "tenant_id": str(value.tenant_id),
            "scopes": sorted(scope.value for scope in value.scopes),
        }

    @app.post("/api/logout")
    async def logout(request: Request, response: Response) -> dict[str, str]:
        require_csrf(request)
        auth.logout(request.cookies.get("umcp_session"))
        response.delete_cookie("umcp_session", path="/")
        return {"status": "logged_out"}

    @app.get("/api/memories")
    async def list_memories(
        request: Request, query: str = "memory", limit: int = 20, cursor: int = 0
    ) -> dict[str, object]:
        value = principal(request)
        value.requires(Scope.MEMORY_READ)
        if cursor < 0:
            raise HTTPException(status_code=400, detail="invalid request")
        page_size = min(max(limit, 1), 50)
        result = await call(value, "memory.search", {"query": query, "limit": 50})
        memories = result.get("memories")
        if not isinstance(memories, list):
            raise HTTPException(status_code=500, detail="service response invalid")
        page = memories[cursor : cursor + page_size]
        return {
            "memories": page,
            "count": len(page),
            "next_cursor": cursor + len(page) if cursor + len(page) < len(memories) else None,
        }

    @app.post("/api/memories")
    async def create_memory(request: Request, payload: MemoryWriteRequest) -> dict[str, object]:
        value = require_csrf(request)
        value.requires(Scope.MEMORY_WRITE)
        return await call(value, "memory.write", payload.model_dump())

    @app.get("/api/memories/{memory_id}")
    async def get_memory(request: Request, memory_id: str) -> dict[str, object]:
        result = await list_memories(request, query="memory", limit=50)
        items = result.get("memories", [])
        if not isinstance(items, list):
            raise HTTPException(status_code=500, detail="service response invalid")
        for item in items:
            if not isinstance(item, dict):
                continue
            memory = item.get("memory")
            if isinstance(memory, dict) and memory.get("id") == memory_id:
                return cast(dict[str, object], memory)
        raise HTTPException(status_code=404, detail="not found")

    @app.patch("/api/memories/{memory_id}")
    async def update_memory(
        request: Request, memory_id: str, payload: MemoryUpdateRequest
    ) -> dict[str, object]:
        value = require_csrf(request)
        value.requires(Scope.MEMORY_WRITE)
        return await call(
            value,
            "memory.update",
            {"id": memory_id, **payload.model_dump()},
        )

    @app.delete("/api/memories/{memory_id}")
    async def forget_memory(
        request: Request, memory_id: str, idempotency_key: str
    ) -> dict[str, object]:
        value = require_csrf(request)
        value.requires(Scope.MEMORY_DELETE)
        return await call(
            value, "memory.forget", {"id": memory_id, "idempotency_key": idempotency_key}
        )

    @app.get("/api/connections")
    async def list_connections(request: Request) -> dict[str, object]:
        value = principal(request)
        value.requires(Scope.CONNECTIONS_MANAGE)
        items = [
            item for item in auth._connections.values() if item["tenant_id"] == str(value.tenant_id)
        ]
        return {"connections": items, "count": len(items)}

    @app.post("/api/connections")
    async def create_connection(request: Request, payload: ConnectionRequest) -> dict[str, object]:
        value = require_csrf(request)
        value.requires(Scope.CONNECTIONS_MANAGE)
        connection_id = "conn_" + secrets.token_urlsafe(12)
        connection: dict[str, object] = {
            "id": connection_id,
            "name": payload.name,
            "scopes": sorted(scope.value for scope in payload.scopes),
            "tenant_id": str(value.tenant_id),
            "status": "active",
        }
        auth._connections[connection_id] = connection
        return {
            "connection": connection,
            "receipt": auth.receipt("connection.created", value, "done"),
        }

    @app.post("/api/connections/{connection_id}/revoke")
    async def revoke_connection(request: Request, connection_id: str) -> dict[str, object]:
        value = require_csrf(request)
        value.requires(Scope.CONNECTIONS_MANAGE)
        connection = auth._connections.get(connection_id)
        if connection is None or connection["tenant_id"] != str(value.tenant_id):
            raise HTTPException(status_code=404, detail="not found")
        connection["status"] = "revoked"
        return {
            "connection": connection,
            "receipt": auth.receipt("connection.revoked", value, "done"),
        }

    @app.post("/api/agent-credentials")
    async def create_agent_credential(
        request: Request, payload: AgentCredentialRequest
    ) -> dict[str, object]:
        value = require_csrf(request)
        value.requires(Scope.CONNECTIONS_MANAGE)
        raw = "umcp_pat_" + secrets.token_urlsafe(32)
        credential_id = "cred_" + secrets.token_urlsafe(12)
        token_digest = hashlib.sha256(raw.encode()).hexdigest()
        auth._agent_credentials[credential_id] = {
            "id": credential_id,
            "name": payload.name,
            "tenant_id": str(value.tenant_id),
            "scopes": sorted(scope.value for scope in payload.scopes),
            "_token_digest": token_digest,
            "_subject_id": str(value.subject_id),
            "_membership_id": str(value.membership_id),
            "_credential_id": str(uuid4()),
            "expires_at": (datetime.now(UTC) + timedelta(seconds=payload.expires_in_seconds))
            .isoformat()
            .replace("+00:00", "Z"),
            "revoked": False,
        }
        auth._agent_token_index[token_digest] = credential_id
        # The raw secret is returned exactly once and never retained by this adapter.
        public_credential = {
            key: item
            for key, item in auth._agent_credentials[credential_id].items()
            if not key.startswith("_")
        }
        return {"credential": public_credential, "token": raw}

    @app.get("/api/agent-credentials")
    async def list_agent_credentials(request: Request) -> dict[str, object]:
        value = principal(request)
        value.requires(Scope.CONNECTIONS_MANAGE)
        credentials = [
            {key: item for key, item in credential.items() if not key.startswith("_")}
            for credential in auth._agent_credentials.values()
            if credential["tenant_id"] == str(value.tenant_id)
        ]
        return {"credentials": credentials, "count": len(credentials)}

    @app.post("/api/agent-credentials/{credential_id}/revoke")
    async def revoke_agent_credential(request: Request, credential_id: str) -> dict[str, object]:
        value = require_csrf(request)
        value.requires(Scope.CONNECTIONS_MANAGE)
        credential = auth._agent_credentials.get(credential_id)
        if credential is None or credential["tenant_id"] != str(value.tenant_id):
            raise HTTPException(status_code=404, detail="not found")
        credential["revoked"] = True
        return {"receipt": auth.receipt("agent_credential.revoked", value, "done")}

    @app.post("/api/exports")
    async def request_export(request: Request) -> dict[str, object]:
        value = require_csrf(request)
        value.requires(Scope.MEMORY_EXPORT)
        return {"receipt": auth.receipt("tenant.export", value, "accepted")}

    @app.get("/api/operations/{operation_id}")
    async def operation_status(request: Request, operation_id: str) -> dict[str, object]:
        value = principal(request)
        operation = auth._operations.get(operation_id)
        if operation is None or operation["tenant_id"] != str(value.tenant_id):
            raise HTTPException(status_code=404, detail="not found")
        return {"receipt": operation}

    @app.post("/api/account-deletions")
    async def request_account_deletion(request: Request) -> dict[str, object]:
        value = require_csrf(request)
        return {"receipt": auth.receipt("account.deletion", value, "accepted")}

    return app


def _redact_owner(value: object) -> None:
    if isinstance(value, dict):
        value.pop("owner_id", None)
        for child in value.values():
            _redact_owner(child)
    elif isinstance(value, list):
        for child in value:
            _redact_owner(child)
