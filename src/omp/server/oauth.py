"""Small, fail-closed OAuth authorization server for the hosted MCP boundary.

Only digests of browser state, authorization codes and bearer tokens are
persisted.  The Google client credentials are read by the runtime from a
Secret Manager reference; they are never logged or returned.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from mcp.server.auth.provider import AccessToken
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from omp.cloud import Scope

_SCOPES = frozenset(item.value for item in Scope if item in {Scope.MEMORY_READ, Scope.MEMORY_WRITE, Scope.MEMORY_DELETE})
_SHA256_HEX = 64
_STATE_TTL = timedelta(minutes=10)
_CODE_TTL = timedelta(minutes=2)
_ACCESS_TTL = timedelta(minutes=10)
_REFRESH_TTL = timedelta(days=7)


class OAuthError(PermissionError):
    def __init__(self, code: str, *, status: int = 400) -> None:
        super().__init__(code)
        self.code, self.status = code, status


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _random(prefix: str) -> str:
    return prefix + secrets.token_urlsafe(32)


def _pkce(verifier: str) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).rstrip(b"=").decode("ascii")


def _valid_client_redirect_uri(value: str) -> bool:
    try:
        parsed = urllib.parse.urlsplit(value)
    except ValueError:
        return False
    if (
        not parsed.netloc
        or parsed.username
        or parsed.password
        or parsed.fragment
        or parsed.query
    ):
        return False
    if parsed.scheme == "https":
        return bool(parsed.hostname)
    if parsed.scheme == "http":
        return parsed.hostname in {"127.0.0.1", "::1"}
    return False


def _https_uri(value: str) -> bool:
    try:
        parsed = urllib.parse.urlsplit(value)
    except ValueError:
        return False
    return (
        parsed.scheme == "https"
        and bool(parsed.netloc)
        and not parsed.username
        and not parsed.password
        and not parsed.fragment
    )



def _valid_pkce_challenge(value: str) -> bool:
    try:
        value.encode("ascii")
    except UnicodeEncodeError:
        return False
    return len(value) == 43 and all(char.isalnum() or char in "-_" for char in value)


@dataclass(frozen=True, slots=True)
class OAuthConfiguration:
    issuer: str
    google_client_id: str
    google_client_secret: str = field(repr=False)
    google_redirect_uri: str
    clients: dict[str, str]
    allowed_email_digests: frozenset[str]

    @classmethod
    def from_settings(cls, settings: Any) -> OAuthConfiguration | None:
        raw = settings.oauth_google_credentials.get_secret_value().strip()
        public_client_id = settings.oauth_google_client_id.strip()
        google_redirect_uri = settings.oauth_google_redirect_uri.strip()
        issuer = settings.public_base_url.rstrip("/")
        clients_raw = settings.oauth_clients.strip()
        allowed = frozenset(item.strip().lower() for item in settings.oauth_allowed_email_sha256.split(",") if item.strip())
        if (
            not raw
            or not public_client_id
            or not google_redirect_uri
            or not clients_raw
            or len(allowed) != 1
            or not all(len(item) == _SHA256_HEX and all(char in "0123456789abcdef" for char in item) for item in allowed)
            or not _https_uri(issuer)
            or google_redirect_uri != issuer + "/oauth/callback"
            or not _https_uri(google_redirect_uri)
        ):
            return None
        try:
            decoded = json.loads(raw)
        except json.JSONDecodeError:
            # Secret Manager may hold only the confidential half.  The Google
            # client id remains a separately supplied public setting.
            client_secret = raw
        else:
            payload = decoded.get("web", decoded) if isinstance(decoded, dict) else None
            if not isinstance(payload, dict) or "client_secret" not in payload:
                return None
            if not isinstance(payload.get("client_id"), str) or payload["client_id"].strip() != public_client_id:
                return None
            if not isinstance(payload["client_secret"], str):
                return None
            client_secret = payload["client_secret"].strip()
        try:
            clients = json.loads(clients_raw)
            if not isinstance(clients, dict) or not clients or not all(
                isinstance(k, str) and bool(k.strip()) and isinstance(v, str) and _valid_client_redirect_uri(v)
                for k, v in clients.items()
            ):
                return None
        except (KeyError, TypeError, ValueError):
            return None
        if not client_secret:
            return None
        return cls(issuer, public_client_id, client_secret, google_redirect_uri, dict(clients), allowed)


class OAuthServer:
    def __init__(self, engine: AsyncEngine, config: OAuthConfiguration) -> None:
        self.engine, self.config = engine, config

    def metadata(self) -> dict[str, Any]:
        base = self.config.issuer
        return {"issuer": base, "authorization_endpoint": base + "/authorize", "token_endpoint": base + "/token", "revocation_endpoint": base + "/revoke", "response_types_supported": ["code"], "grant_types_supported": ["authorization_code", "refresh_token"], "code_challenge_methods_supported": ["S256"], "token_endpoint_auth_methods_supported": ["none"], "authorization_response_iss_parameter_supported": True, "scopes_supported": sorted(_SCOPES)}

    async def begin(self, client_id: str, redirect_uri: str, scope: str, state: str, challenge: str, method: str) -> str:
        requested = frozenset(scope.split())
        if (
            self.config.clients.get(client_id) != redirect_uri
            or not state
            or method != "S256"
            or not _valid_pkce_challenge(challenge)
            or not requested
            or not requested <= _SCOPES
        ):
            raise OAuthError("invalid_request")
        value = _random("st_")
        async with self.engine.begin() as conn:
            await conn.execute(text("INSERT INTO oauth_states (state_digest, client_id, redirect_uri, client_state, code_challenge, scopes, expires_at) VALUES (:d,:c,:r,:cs,:p,:s,:e)"), {"d": _digest(value), "c": client_id, "r": redirect_uri, "cs": state, "p": challenge, "s": sorted(requested), "e": datetime.now(UTC) + _STATE_TTL})
        query = urllib.parse.urlencode({"client_id": self.config.google_client_id, "redirect_uri": self.config.google_redirect_uri, "response_type": "code", "scope": "openid email", "state": value, "prompt": "select_account"})
        return "https://accounts.google.com/o/oauth2/v2/auth?" + query

    async def callback(self, code: str, state: str) -> tuple[str, str, str]:
        if not code or not state:
            raise OAuthError("invalid_request")
        async with self.engine.begin() as conn:
            row = (await conn.execute(text("UPDATE oauth_states SET used_at=now() WHERE state_digest=:d AND used_at IS NULL AND expires_at>now() RETURNING client_id,redirect_uri,client_state,code_challenge,scopes,state_digest"), {"d": _digest(state)})).mappings().first()
            if row is None:
                raise OAuthError("invalid_state")
            claims = self._google_claims(code)
            email = str(claims.get("email", "")).strip().lower()
            subject = str(claims.get("sub", ""))
            if str(claims.get("email_verified", "")).lower() != "true" or not email or not subject or _digest(email) not in self.config.allowed_email_digests:
                raise OAuthError("access_denied", status=403)
            subject_id = uuid5(NAMESPACE_URL, "umcp/google/subject/" + subject)
            tenant_id = uuid5(NAMESPACE_URL, "umcp/google/test-tenant/" + subject)
            membership_id = uuid5(NAMESPACE_URL, "umcp/google/membership/" + subject)
            credential_id = uuid4()
            await self._ensure_identity(conn, subject_id, tenant_id, membership_id, subject)
            raw_code = _random("ac_")
            await conn.execute(text("INSERT INTO oauth_authorization_codes (code_digest,state_digest,client_id,redirect_uri,subject_id,tenant_id,membership_id,credential_id,scopes,code_challenge,expires_at) VALUES (:d,:sd,:c,:r,:u,:t,:m,:k,:s,:p,:e)"), {"d": _digest(raw_code), "sd": row["state_digest"], "c": row["client_id"], "r": row["redirect_uri"], "u": subject_id, "t": tenant_id, "m": membership_id, "k": credential_id, "s": row["scopes"], "p": row["code_challenge"], "e": datetime.now(UTC) + _CODE_TTL})
        return row["redirect_uri"], raw_code, row["client_state"]

    async def token(self, form: dict[str, str]) -> dict[str, Any]:
        grant = form.get("grant_type", "")
        if grant == "authorization_code":
            verifier, raw = form.get("code_verifier", ""), form.get("code", "")
            async with self.engine.begin() as conn:
                row = (await conn.execute(text("UPDATE oauth_authorization_codes SET used_at=now() WHERE code_digest=:d AND used_at IS NULL AND expires_at>now() RETURNING client_id,redirect_uri,subject_id,tenant_id,membership_id,credential_id,scopes,code_challenge"), {"d": _digest(raw)})).mappings().first()
                try:
                    pkce_valid = bool(verifier) and hmac.compare_digest(_pkce(verifier), row["code_challenge"]) if row is not None else False
                except (UnicodeError, ValueError):
                    pkce_valid = False
                if row is None or form.get("client_id") != row["client_id"] or form.get("redirect_uri") != row["redirect_uri"] or not pkce_valid:
                    raise OAuthError("invalid_grant")
                return await self._issue(conn, row)
        if grant == "refresh_token":
            async with self.engine.begin() as conn:
                row = (await conn.execute(text("UPDATE oauth_tokens SET revoked_at=now() WHERE token_digest=:d AND token_kind='refresh' AND revoked_at IS NULL AND expires_at>now() RETURNING client_id,subject_id,tenant_id,membership_id,credential_id,scopes"), {"d": _digest(form.get("refresh_token", ""))})).mappings().first()
                if row is None or form.get("client_id") != row["client_id"]:
                    raise OAuthError("invalid_grant")
                return await self._issue(conn, row)
        raise OAuthError("unsupported_grant_type")

    async def revoke(self, token: str) -> None:
        if token:
            async with self.engine.begin() as conn:
                await conn.execute(text("UPDATE oauth_tokens SET revoked_at=COALESCE(revoked_at, now()) WHERE token_digest=:d"), {"d": _digest(token)})

    async def verify_token(self, token: str) -> AccessToken | None:
        async with self.engine.connect() as conn:
            row = (await conn.execute(text("SELECT client_id,subject_id,tenant_id,membership_id,credential_id,scopes,expires_at FROM oauth_tokens WHERE token_digest=:d AND token_kind='access' AND revoked_at IS NULL AND expires_at>now()"), {"d": _digest(token)})).mappings().first()
        if row is None:
            return None
        return AccessToken(token=token, client_id=row["client_id"], scopes=list(row["scopes"]), expires_at=int(row["expires_at"].timestamp()), resource=self.config.issuer + "/mcp", subject=str(row["subject_id"]), claims={"iss": self.config.issuer, "tenant_id": str(row["tenant_id"]), "membership_id": str(row["membership_id"]), "credential_id": str(row["credential_id"])})

    async def _issue(self, conn: Any, row: Any) -> dict[str, Any]:
        access, refresh, family = _random("at_"), _random("rt_"), uuid4()
        now = datetime.now(UTC)
        for value, kind, expiry in ((access, "access", now + _ACCESS_TTL), (refresh, "refresh", now + _REFRESH_TTL)):
            await conn.execute(text("INSERT INTO oauth_tokens (token_digest,token_kind,client_id,subject_id,tenant_id,membership_id,credential_id,scopes,expires_at,family_id) VALUES (:d,:k,:c,:u,:t,:m,:i,:s,:e,:f)"), {"d": _digest(value), "k": kind, "c": row["client_id"], "u": row["subject_id"], "t": row["tenant_id"], "m": row["membership_id"], "i": row["credential_id"], "s": row["scopes"], "e": expiry, "f": family})
        return {"access_token": access, "refresh_token": refresh, "token_type": "Bearer", "expires_in": int(_ACCESS_TTL.total_seconds()), "scope": " ".join(row["scopes"])}

    async def _ensure_identity(self, conn: Any, user: UUID, tenant: UUID, membership: UUID, subject: str) -> None:
        await conn.execute(text("INSERT INTO tenants (id,name) VALUES (:t,'staging-test') ON CONFLICT (id) DO NOTHING"), {"t": tenant})
        await conn.execute(text("INSERT INTO users (id) VALUES (:u) ON CONFLICT (id) DO NOTHING"), {"u": user})
        await conn.execute(text("SELECT set_config('app.tenant_id', :t, true)"), {"t": str(tenant)})
        await conn.execute(text("INSERT INTO memberships (id,tenant_id,user_id,role) VALUES (:m,:t,:u,'owner') ON CONFLICT (tenant_id,user_id) DO NOTHING"), {"m": membership, "t": tenant, "u": user})
        await conn.execute(text("INSERT INTO identities (id,tenant_id,user_id,issuer,subject) VALUES (:i,:t,:u,'https://accounts.google.com',:s) ON CONFLICT (issuer,subject) DO NOTHING"), {"i": uuid5(NAMESPACE_URL, "umcp/google/identity/" + subject), "t": tenant, "u": user, "s": subject})

    def _google_claims(self, code: str) -> dict[str, Any]:
        body = urllib.parse.urlencode({"code": code, "client_id": self.config.google_client_id, "client_secret": self.config.google_client_secret, "redirect_uri": self.config.google_redirect_uri, "grant_type": "authorization_code"}).encode()
        try:
            with urllib.request.urlopen(urllib.request.Request("https://oauth2.googleapis.com/token", body, {"Content-Type": "application/x-www-form-urlencoded"}), timeout=10) as response:
                token_response = json.loads(response.read())
                token = token_response["id_token"]
            with urllib.request.urlopen("https://oauth2.googleapis.com/tokeninfo?id_token=" + urllib.parse.quote(token), timeout=10) as response:
                claims = json.loads(response.read())
        except Exception as exc:
            raise OAuthError("invalid_identity", status=401) from exc
        if not isinstance(claims, dict):
            raise OAuthError("invalid_identity", status=401)
        try:
            expired = int(claims.get("exp", 0)) <= int(datetime.now(UTC).timestamp())
        except (TypeError, ValueError):
            expired = True
        if claims.get("aud") != self.config.google_client_id or claims.get("iss") not in {"accounts.google.com", "https://accounts.google.com"} or expired:
            raise OAuthError("invalid_identity", status=401)
        return claims
