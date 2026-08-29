"""OAuth 2.0 PKCE client and session management for UMCP Cloud SDK."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import time
import urllib.parse
from dataclasses import dataclass
from typing import Any, Mapping
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from .client import ProtocolError


@dataclass
class TokenData:
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: str | None = None
    scope: str = ""
    issued_at: float = 0.0

    @property
    def is_expired(self) -> bool:
        # Buffer of 15 seconds before official expiry
        return (time.time() - self.issued_at) > (self.expires_in - 15)


def generate_pkce_pair() -> tuple[str, str]:
    """Generate (code_verifier, code_challenge) using S256."""
    raw_verifier = os.urandom(32)
    code_verifier = base64.urlsafe_b64encode(raw_verifier).decode().rstrip("=")
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).decode().rstrip("=")
    return code_verifier, code_challenge


class OAuthSession:
    """Manages OAuth 2.0 PKCE discovery, token exchange, rotation, and revocation."""

    def __init__(
        self,
        base_url: str,
        *,
        client_id: str = "umcp-staging-h07-audit",
        redirect_uri: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.client_id = client_id
        self.redirect_uri = redirect_uri or f"{self.base_url}/oauth/callback"
        self.timeout = timeout
        self._tokens: TokenData | None = None
        self._protected_resource_metadata: dict[str, Any] | None = None
        self._auth_server_metadata: dict[str, Any] | None = None

    def discover_protected_resource(self) -> dict[str, Any]:
        """Fetch protected resource metadata."""
        url = f"{self.base_url}/.well-known/oauth-protected-resource/mcp"
        req = Request(url, headers={"Accept": "application/json"})
        try:
            with urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode())
                self._protected_resource_metadata = data
                return data
        except (HTTPError, URLError, json.JSONDecodeError) as exc:
            raise ProtocolError("discovery_failed", f"Failed to fetch protected resource metadata: {exc}") from exc

    def discover_authorization_server(self) -> dict[str, Any]:
        """Fetch authorization server metadata."""
        url = f"{self.base_url}/.well-known/oauth-authorization-server"
        req = Request(url, headers={"Accept": "application/json"})
        try:
            with urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode())
                self._auth_server_metadata = data
                return data
        except (HTTPError, URLError, json.JSONDecodeError) as exc:
            raise ProtocolError("discovery_failed", f"Failed to fetch authorization server metadata: {exc}") from exc

    def get_authorization_url(
        self,
        *,
        state: str,
        code_challenge: str,
        scopes: list[str] | None = None,
    ) -> str:
        """Construct the authorization URL with PKCE parameters."""
        scope_str = " ".join(scopes or ["memory:read", "memory:write", "memory:delete", "memory:export", "connections:manage"])
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": scope_str,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        return f"{self.base_url}/authorize?{urllib.parse.urlencode(params)}"

    def exchange_code(
        self,
        *,
        code: str,
        code_verifier: str,
        redirect_uri: str | None = None,
    ) -> TokenData:
        """Exchange an authorization code for access and refresh tokens."""
        url = f"{self.base_url}/token"
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": self.client_id,
            "redirect_uri": redirect_uri or self.redirect_uri,
            "code_verifier": code_verifier,
        }
        data = self._post_form(url, payload)
        token_data = TokenData(
            access_token=data["access_token"],
            token_type=data.get("token_type", "Bearer"),
            expires_in=int(data.get("expires_in", 3600)),
            refresh_token=data.get("refresh_token"),
            scope=data.get("scope", ""),
            issued_at=time.time(),
        )
        self._tokens = token_data
        return token_data

    def refresh(self) -> TokenData:
        """Refresh the access token using the current refresh token."""
        if not self._tokens or not self._tokens.refresh_token:
            raise ProtocolError("unauthorized", "No refresh token available")
        url = f"{self.base_url}/token"
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": self._tokens.refresh_token,
            "client_id": self.client_id,
        }
        data = self._post_form(url, payload)
        token_data = TokenData(
            access_token=data["access_token"],
            token_type=data.get("token_type", "Bearer"),
            expires_in=int(data.get("expires_in", 3600)),
            refresh_token=data.get("refresh_token") or self._tokens.refresh_token,
            scope=data.get("scope", self._tokens.scope),
            issued_at=time.time(),
        )
        self._tokens = token_data
        return token_data

    def revoke(self, token: str | None = None, token_type_hint: str = "access_token") -> bool:
        """Revoke an access or refresh token."""
        target_token = token or (self._tokens.access_token if self._tokens else None)
        if not target_token:
            return True
        url = f"{self.base_url}/revoke"
        payload = {
            "token": target_token,
            "token_type_hint": token_type_hint,
            "client_id": self.client_id,
        }
        self._post_form(url, payload)
        if token is None or (self._tokens and token == self._tokens.access_token):
            self._tokens = None
        return True

    def get_valid_access_token(self) -> str:
        """Return a valid access token, automatically refreshing if expired."""
        if not self._tokens:
            raise ProtocolError("unauthorized", "Session is not authenticated")
        if self._tokens.is_expired and self._tokens.refresh_token:
            self.refresh()
        return self._tokens.access_token

    def set_tokens(self, token_data: TokenData) -> None:
        """Directly inject active tokens into the session."""
        self._tokens = token_data

    def _post_form(self, url: str, form_data: Mapping[str, str]) -> dict[str, Any]:
        body = urllib.parse.urlencode(form_data).encode("utf-8")
        req = Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode()
                return json.loads(raw) if raw else {}
        except HTTPError as exc:
            status = exc.code
            try:
                err_body = json.loads(exc.read().decode())
                err_code = err_body.get("error", "http_error")
                err_desc = err_body.get("error_description", str(exc))
            except Exception:
                err_code = f"http_{status}"
                err_desc = str(exc)
            raise ProtocolError(err_code, err_desc) from exc
        except (URLError, json.JSONDecodeError) as exc:
            raise ProtocolError("network_error", f"Request to {url} failed: {exc}") from exc
