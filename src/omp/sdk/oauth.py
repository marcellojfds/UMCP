"""OAuth 2.0 PKCE client and loopback session management for UMCP Cloud SDK."""

from __future__ import annotations

import base64
import hashlib
import http.server
import json
import os
import threading
import time
import urllib.parse
import webbrowser
from dataclasses import dataclass
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .client import ProtocolError

DEFAULT_CLIENT_ID = "umcp-python-sdk"
DEFAULT_LOOPBACK_REDIRECT = "http://127.0.0.1:8765/callback"
DEFAULT_SCOPES = ["memory:read", "memory:write", "memory:delete"]


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


def _validate_loopback_redirect_uri(redirect_uri: str) -> tuple[str, int, str]:
    """Validate that the redirect URI is a literal loopback IPv4/IPv6 address."""
    parsed = urllib.parse.urlsplit(redirect_uri)
    if parsed.scheme != "http":
        raise ValueError("Loopback redirect URI must use http:// scheme")
    if parsed.hostname not in {"127.0.0.1", "::1"}:
        raise ValueError(f"Loopback redirect URI host must be literal 127.0.0.1 or ::1, got: {parsed.hostname}")
    if parsed.username or parsed.password or parsed.fragment or parsed.query:
        raise ValueError("Loopback redirect URI must not contain userinfo, fragment or query")
    port = parsed.port or 8765
    path = parsed.path or "/callback"
    return str(parsed.hostname), port, path


class _LoopbackCallbackHandler(http.server.BaseHTTPRequestHandler):
    """Silent HTTP request handler for capturing OAuth authorization code."""

    def log_message(self, format: str, *args: Any) -> None:
        # Suppress access logs to avoid recording codes, state or paths
        pass

    def do_GET(self) -> None:
        parsed = urllib.parse.urlsplit(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        server: _LoopbackServer = self.server  # type: ignore

        if parsed.path == server.expected_path:
            server.received_code = params.get("code", [""])[0]
            server.received_state = params.get("state", [""])[0]
            server.received_error = params.get("error", [""])[0]

            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(
                b"<!DOCTYPE html><html><body style='font-family:sans-serif;padding:40px;text-align:center;'>"
                b"<h2>UMCP Authentication Complete</h2>"
                b"<p>You can close this tab and return to the application.</p>"
                b"</body></html>"
            )
        else:
            self.send_response(404)
            self.end_headers()


class _LoopbackServer(http.server.HTTPServer):
    def __init__(self, host: str, port: int, path: str) -> None:
        super().__init__((host, port), _LoopbackCallbackHandler)
        self.expected_path = path
        self.received_code: str = ""
        self.received_state: str = ""
        self.received_error: str = ""


class OAuthSession:
    """Manages OAuth 2.0 PKCE discovery, loopback login, token rotation, and revocation."""

    def __init__(
        self,
        base_url: str,
        *,
        client_id: str = DEFAULT_CLIENT_ID,
        redirect_uri: str = DEFAULT_LOOPBACK_REDIRECT,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.client_id = client_id
        self.redirect_uri = redirect_uri
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
        selected_scopes = scopes or DEFAULT_SCOPES
        for sc in selected_scopes:
            if sc not in {"memory:read", "memory:write", "memory:delete"}:
                raise ValueError(f"Scope {sc} is not supported by UMCP authorization server")
        scope_str = " ".join(selected_scopes)
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

    def login_via_loopback(
        self,
        *,
        scopes: list[str] | None = None,
        timeout: float = 120.0,
        open_browser: bool = True,
    ) -> TokenData:
        """Start ephemeral loopback server, open browser for consent, and exchange code."""
        host, port, path = _validate_loopback_redirect_uri(self.redirect_uri)
        code_verifier, code_challenge = generate_pkce_pair()
        state = base64.urlsafe_b64encode(os.urandom(24)).decode().rstrip("=")

        auth_url = self.get_authorization_url(
            state=state,
            code_challenge=code_challenge,
            scopes=scopes,
        )

        server = _LoopbackServer(host, port, path)
        server.timeout = 1.0

        def _run_server() -> None:
            deadline = time.time() + timeout
            while time.time() < deadline:
                if server.received_code or server.received_error:
                    break
                server.handle_request()

        thread = threading.Thread(target=_run_server, daemon=True)
        thread.start()

        if open_browser:
            webbrowser.open(auth_url)

        thread.join(timeout=timeout)
        server.server_close()

        if server.received_error:
            raise ProtocolError("access_denied", f"Authorization server returned error: {server.received_error}")
        if not server.received_code:
            raise ProtocolError("timeout", "OAuth callback loopback server timed out waiting for authorization code")
        if server.received_state != state:
            raise ProtocolError("invalid_state", "State parameter mismatch in OAuth callback")

        return self.exchange_code(
            code=server.received_code,
            code_verifier=code_verifier,
            redirect_uri=self.redirect_uri,
        )

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
            expires_in=int(data.get("expires_in", 600)),
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
        old_token = self._tokens.access_token
        url = f"{self.base_url}/token"
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": self._tokens.refresh_token,
            "client_id": self.client_id,
        }
        data = self._post_form(url, payload)
        new_access = data["access_token"]
        new_refresh = data.get("refresh_token") or self._tokens.refresh_token
        if new_access == old_token:
            raise ProtocolError("rotation_failed", "Access token was not rotated upon refresh")
        token_data = TokenData(
            access_token=new_access,
            token_type=data.get("token_type", "Bearer"),
            expires_in=int(data.get("expires_in", 600)),
            refresh_token=new_refresh,
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
        if not self._tokens or not self._tokens.access_token:
            raise ProtocolError("unauthorized", "Session is not authenticated")
        if self._tokens.is_expired and self._tokens.refresh_token:
            self.refresh()
        return self._tokens.access_token

    def set_tokens(self, token_data: TokenData) -> None:
        """Inject active tokens into session (used for test harnesses)."""
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
