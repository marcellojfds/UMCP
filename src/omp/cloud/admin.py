"""Local-only administrative API with passwordless session semantics."""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from omp.cloud.security import Principal, Scope


class _Request(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MagicLinkRequest(_Request):
    email: str = Field(min_length=3, max_length=320)
    redirect: str = "/"


@dataclass(slots=True)
class _MagicLink:
    digest: str
    principal: Principal
    expires_at: datetime
    used: bool = False


class LocalMailboxAuth:
    """Development mailbox sink; tokens are single-use and only token digests persist."""

    def __init__(self, *, secure_cookies: bool = False) -> None:
        self.secure_cookies = secure_cookies
        self.outbox: list[dict[str, str]] = []
        self._links: dict[str, _MagicLink] = {}
        self._sessions: dict[str, Principal] = {}
        self._csrf: dict[str, str] = {}

    def request(self, email: str) -> None:
        # Non-enumerating response. A deterministic local principal makes the
        # development integration usable without storing real identities.
        principal = Principal(
            subject_id=uuid4(),
            tenant_id=uuid4(),
            membership_id=uuid4(),
            credential_id=uuid4(),
            scopes=frozenset(Scope),
            auth_method="local-magic-link",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        raw = secrets.token_urlsafe(32)
        digest = hashlib.sha256(raw.encode()).hexdigest()
        self._links[digest] = _MagicLink(
            digest, principal, datetime.now(UTC) + timedelta(minutes=10)
        )
        self.outbox.append({"to": "captured", "token": raw})

    def consume(self, raw: str) -> tuple[str, str] | None:
        link = self._links.get(hashlib.sha256(raw.encode()).hexdigest())
        if link is None or link.used or link.expires_at <= datetime.now(UTC):
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


def create_admin_app(auth: LocalMailboxAuth) -> FastAPI:
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

    @app.get("/api/capabilities")
    async def capabilities() -> dict[str, object]:
        return {
            "version": "umcp.admin.v1",
            "auth": "local_magic_link",
            "email_delivery": "captured",
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
            "tenant_id": str(value.tenant_id),
            "scopes": sorted(scope.value for scope in value.scopes),
        }

    @app.post("/api/logout")
    async def logout(request: Request, response: Response) -> dict[str, str]:
        require_csrf(request)
        auth.logout(request.cookies.get("umcp_session"))
        response.delete_cookie("umcp_session", path="/")
        return {"status": "logged_out"}

    return app
