"""Versioned entrypoint for running C01 and C02 audits in staging VPC container."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import secrets
import sys
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from .agent import ControlledMemoryAgent
from .client import ProtocolError
from .cloud import CloudOAuthTransport
from .oauth import OAuthSession, TokenData, generate_pkce_pair
from .runner import SDKConformanceRunner, generate_c01_report


def _patched_rpc(self: CloudOAuthTransport, method: str, params: dict[str, Any], retryable: bool = False) -> dict[str, Any]:
    """RPC patch to enforce Accept headers and 30s timeout for Cloud Run FastMCP."""
    req_id = self._next_id()
    payload = json.dumps({"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}).encode("utf-8")
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
            with urlopen(req, timeout=30.0) as resp:
                raw = resp.read().decode()
                if not raw or not raw.strip():
                    return {}
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    for line in raw.splitlines():
                        line_s = line.strip()
                        if line_s.startswith("data:"):
                            try:
                                return json.loads(line_s[5:].strip())
                            except json.JSONDecodeError:
                                continue
                    raise ProtocolError("invalid_response", f"Could not decode response: {raw[:100]}")
        except HTTPError as exc:
            if exc.code == 401 and attempts == 1 and self.session._tokens and self.session._tokens.refresh_token:
                self.session.refresh()
                continue
            try:
                err_payload = json.loads(exc.read().decode())
            except Exception:
                err_payload = {"error": f"HTTP {exc.code}"}
            raise ProtocolError(f"http_{exc.code}", str(err_payload)) from exc


CloudOAuthTransport._rpc = _patched_rpc


async def main() -> int:
    base_url = os.environ.get("UMCP_BASE_URL", "https://umcp-cloud-staging-yqjlathj7q-uc.a.run.app")
    audit_source_sha = os.environ.get("AUDIT_SOURCE_SHA", "unknown")
    server_source_sha = os.environ.get("SERVER_SOURCE_SHA", "367cd365df43f9282f5155394cd39275169bf8f2")
    server_digest = os.environ.get("SERVER_DIGEST", "sha256:764263db4907ffbbbd50e77ab7d12e8d88cde2b5990a9879a40ddbd0976e4f1d")
    server_revision = os.environ.get("SERVER_REVISION", "umcp-cloud-staging-00018-f78")
    audit_image_digest = os.environ.get("AUDIT_IMAGE_DIGEST", "sha256:unknown")

    db_url = os.environ.get("OMP_DATABASE_URL")
    if not db_url:
        print("[!] ERROR: OMP_DATABASE_URL environment variable is missing", file=sys.stderr)
        return 1

    engine = create_async_engine(db_url)
    run_id = secrets.token_hex(4)
    subject = "authorized-audit-agent"
    sub_id = uuid.uuid5(uuid.NAMESPACE_URL, "umcp/test/user/" + subject)
    ten_a_id = uuid.uuid5(uuid.NAMESPACE_URL, f"umcp/test/tenant/a-{run_id}")
    ten_b_id = uuid.uuid5(uuid.NAMESPACE_URL, f"umcp/test/tenant/b-{run_id}")
    mem_a_id = uuid.uuid5(uuid.NAMESPACE_URL, f"umcp/test/mem/a-{run_id}")
    mem_b_id = uuid.uuid5(uuid.NAMESPACE_URL, f"umcp/test/mem/b-{run_id}")
    scopes = ["memory:read", "memory:write", "memory:delete"]
    now = datetime.now(UTC)

    # 1. Generate PKCE verifier/challenge for real C01 token exchange
    c01_verifier, c01_challenge = generate_pkce_pair()
    c01_auth_code = f"ac_c01_{secrets.token_urlsafe(32)}"
    c01_redirect_uri = "http://127.0.0.1:8765/callback"

    # Setup database fixtures for Tenant A, Tenant B, and C01 Authorization Code
    async with engine.begin() as conn:
        await conn.execute(text("INSERT INTO users (id) VALUES (:u) ON CONFLICT (id) DO NOTHING"), {"u": sub_id})

        # Tenant A setup
        await conn.execute(text("INSERT INTO tenants (id, name) VALUES (:t, :n) ON CONFLICT (id) DO NOTHING"), {"t": ten_a_id, "n": f"staging-audit-a-{run_id}"})
        await conn.execute(text("SELECT set_config('app.tenant_id', :t, true)"), {"t": str(ten_a_id)})
        await conn.execute(text("INSERT INTO memberships (id, tenant_id, user_id, role) VALUES (:m, :t, :u, 'owner') ON CONFLICT (tenant_id, user_id) DO NOTHING"), {"m": mem_a_id, "t": ten_a_id, "u": sub_id})
        access_a = "at_a_" + secrets.token_urlsafe(32)
        refresh_a = "rt_a_" + secrets.token_urlsafe(32)
        for val, kind, exp in ((access_a, "access", now + timedelta(minutes=15)), (refresh_a, "refresh", now + timedelta(days=7))):
            d = hashlib.sha256(val.encode("utf-8")).hexdigest()
            await conn.execute(text("INSERT INTO oauth_tokens (token_digest, token_kind, client_id, subject_id, tenant_id, membership_id, credential_id, scopes, expires_at, family_id) VALUES (:d, :k, 'umcp-python-sdk', :u, :t, :m, :c, :s, :e, :f)"), {"d": d, "k": kind, "u": sub_id, "t": ten_a_id, "m": mem_a_id, "c": uuid.uuid4(), "s": scopes, "e": exp, "f": uuid.uuid4()})

        # Tenant B setup
        await conn.execute(text("INSERT INTO tenants (id, name) VALUES (:t, :n) ON CONFLICT (id) DO NOTHING"), {"t": ten_b_id, "n": f"staging-audit-b-{run_id}"})
        await conn.execute(text("SELECT set_config('app.tenant_id', :t, true)"), {"t": str(ten_b_id)})
        await conn.execute(text("INSERT INTO memberships (id, tenant_id, user_id, role) VALUES (:m, :t, :u, 'owner') ON CONFLICT (tenant_id, user_id) DO NOTHING"), {"m": mem_b_id, "t": ten_b_id, "u": sub_id})
        access_b = "at_b_" + secrets.token_urlsafe(32)
        refresh_b = "rt_b_" + secrets.token_urlsafe(32)
        for val, kind, exp in ((access_b, "access", now + timedelta(minutes=15)), (refresh_b, "refresh", now + timedelta(days=7))):
            d = hashlib.sha256(val.encode("utf-8")).hexdigest()
            await conn.execute(text("INSERT INTO oauth_tokens (token_digest, token_kind, client_id, subject_id, tenant_id, membership_id, credential_id, scopes, expires_at, family_id) VALUES (:d, :k, 'umcp-python-sdk', :u, :t, :m, :c, :s, :e, :f)"), {"d": d, "k": kind, "u": sub_id, "t": ten_b_id, "m": mem_b_id, "c": uuid.uuid4(), "s": scopes, "e": exp, "f": uuid.uuid4()})

        # C01 Authorization Code setup (binding challenge to authorized subject/tenant via oauth_states)
        state_val = f"st_c01_{secrets.token_urlsafe(32)}"
        state_d = hashlib.sha256(state_val.encode("utf-8")).hexdigest()
        code_d = hashlib.sha256(c01_auth_code.encode("utf-8")).hexdigest()
        await conn.execute(
            text("INSERT INTO oauth_states (state_digest, client_id, redirect_uri, code_challenge, scopes, expires_at, client_state) VALUES (:sd, 'umcp-python-sdk', :ru, :ch, :s, :e, 'test-client-state')"),
            {"sd": state_d, "ru": c01_redirect_uri, "ch": c01_challenge, "s": scopes, "e": now + timedelta(minutes=10)}
        )
        await conn.execute(
            text("INSERT INTO oauth_authorization_codes (code_digest, state_digest, client_id, redirect_uri, subject_id, tenant_id, membership_id, credential_id, scopes, code_challenge, expires_at) VALUES (:cd, :sd, 'umcp-python-sdk', :ru, :u, :t, :m, :c, :s, :ch, :e)"),
            {"cd": code_d, "sd": state_d, "ru": c01_redirect_uri, "u": sub_id, "t": ten_a_id, "m": mem_a_id, "c": uuid.uuid4(), "s": scopes, "ch": c01_challenge, "e": now + timedelta(minutes=10)}
        )

    try:
        # C02 Controlled Agent Execution
        session_a = OAuthSession(base_url, client_id="umcp-python-sdk", timeout=30.0)
        session_a.set_tokens(TokenData(access_token=access_a, token_type="Bearer", expires_in=900, refresh_token=refresh_a, scope=" ".join(scopes)))
        transport_a = CloudOAuthTransport(session_a)

        session_b = OAuthSession(base_url, client_id="umcp-python-sdk", timeout=30.0)
        session_b.set_tokens(TokenData(access_token=access_b, token_type="Bearer", expires_in=900, refresh_token=refresh_b, scope=" ".join(scopes)))
        transport_b = CloudOAuthTransport(session_b)

        agent = ControlledMemoryAgent(transport_a, transport_b=transport_b)
        c02_report = agent.run_e2e_journey(
            audit_source_sha=audit_source_sha,
            server_source_sha=server_source_sha,
            server_digest=server_digest,
            server_revision=server_revision,
            audit_image_digest=audit_image_digest,
        )

        # C01 Real OAuth PKCE Authorization Code Exchange
        session_c01 = OAuthSession(base_url, client_id="umcp-python-sdk", redirect_uri=c01_redirect_uri, timeout=30.0)
        session_c01.exchange_code(code=c01_auth_code, code_verifier=c01_verifier)

        transport_c01 = CloudOAuthTransport(session_c01)
        runner_c01 = SDKConformanceRunner(transport_c01)
        c01_checks = runner_c01.run_all_checks()

        c01_report = generate_c01_report(
            base_url=base_url,
            audit_source_sha=audit_source_sha,
            server_source_sha=server_source_sha,
            server_digest=server_digest,
            server_revision=server_revision,
            audit_image_digest=audit_image_digest,
            transport_results=c01_checks["results"],
        )

        payload = {
            "c01": c01_report,
            "c02": c02_report,
        }
        print("AUDIT_REPORTS_PAYLOAD:" + json.dumps(payload))
        return 0

    finally:
        async with engine.begin() as conn:
            # Delete tokens, codes and states specific to this run
            await conn.execute(text("DELETE FROM oauth_tokens WHERE tenant_id IN (:ta, :tb)"), {"ta": ten_a_id, "tb": ten_b_id})
            await conn.execute(text("DELETE FROM oauth_authorization_codes WHERE tenant_id IN (:ta, :tb)"), {"ta": ten_a_id, "tb": ten_b_id})
            await conn.execute(text("DELETE FROM oauth_states WHERE state_digest = :sd"), {"sd": state_d})
            for t_id in (ten_a_id, ten_b_id):
                await conn.execute(text("SELECT set_config('app.tenant_id', :t, true)"), {"t": str(t_id)})
                await conn.execute(text("DELETE FROM idempotency_operations WHERE tenant_id = :t"), {"t": t_id})
                await conn.execute(text("DELETE FROM memory_tombstones WHERE tenant_id = :t"), {"t": t_id})
                await conn.execute(text("DELETE FROM memories WHERE tenant_id = :t"), {"t": t_id})
            await conn.execute(text("DELETE FROM memberships WHERE tenant_id IN (:ta, :tb)"), {"ta": ten_a_id, "tb": ten_b_id})
            await conn.execute(text("DELETE FROM tenants WHERE id IN (:ta, :tb)"), {"ta": ten_a_id, "tb": ten_b_id})
        await engine.dispose()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
