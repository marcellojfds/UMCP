"""Versioned entrypoint for running C01 and C02 audits in staging VPC container."""

from __future__ import annotations

import asyncio
import hashlib
import os
import secrets
import sys
import uuid
from datetime import UTC, datetime, timedelta
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from .agent import ControlledMemoryAgent
from .audit_contract import (
    NEGATIVE_PROBES,
    safe_error_detail,
    validate_c01_report,
    validate_c02_report,
    validate_runtime_provenance,
)
from .checksums import compute_canonical_checksum
from .client import ProtocolError
from .cloud import CloudOAuthTransport
from .oauth import OAuthSession, TokenData, generate_pkce_pair
from .runner import SDKConformanceRunner, generate_c01_report


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ValueError(f"required environment field {name} is missing")
    return value


def _unauthenticated_mcp_status(base_url: str) -> int:
    request = Request(
        f"{base_url}/mcp",
        data=b'{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}',
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=30.0) as response:
            return response.status
    except HTTPError as exc:
        return exc.code


async def main() -> int:
    base_url = _required_env("UMCP_BASE_URL")
    audit_cycle_id = _required_env("AUDIT_CYCLE_ID")
    audit_source_sha = _required_env("AUDIT_SOURCE_SHA")
    baked_source_sha = _required_env("UMCP_AUDIT_IMAGE_SOURCE_SHA")
    server_source_sha = _required_env("SERVER_SOURCE_SHA")
    server_digest = _required_env("SERVER_DIGEST")
    server_revision = _required_env("SERVER_REVISION")
    audit_image_digest = _required_env("AUDIT_IMAGE_DIGEST")
    validate_runtime_provenance(
        base_url=base_url,
        audit_cycle_id=audit_cycle_id,
        audit_source_sha=audit_source_sha,
        baked_source_sha=baked_source_sha,
        audit_image_digest=audit_image_digest,
        server_source_sha=server_source_sha,
        server_digest=server_digest,
        server_revision=server_revision,
    )

    db_url = os.environ.get("OMP_DATABASE_URL")
    if not db_url:
        print("[!] ERROR: OMP_DATABASE_URL environment variable is missing", file=sys.stderr)
        return 1

    engine = create_async_engine(db_url)
    run_id = secrets.token_hex(4)
    secret_sentinel = f"UMCPAUDIT_SECRET_{audit_cycle_id}_"
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
    c01_auth_code = f"{secret_sentinel}code_{secrets.token_urlsafe(24)}"
    c01_redirect_uri = "http://127.0.0.1:8765/callback"

    # Setup database fixtures for Tenant A, Tenant B, and C01 Authorization Code
    async with engine.begin() as conn:
        await conn.execute(
            text("INSERT INTO users (id) VALUES (:u) ON CONFLICT (id) DO NOTHING"), {"u": sub_id}
        )

        # Tenant A setup
        await conn.execute(
            text("INSERT INTO tenants (id, name) VALUES (:t, :n) ON CONFLICT (id) DO NOTHING"),
            {"t": ten_a_id, "n": f"staging-audit-a-{run_id}"},
        )
        await conn.execute(
            text("SELECT set_config('app.tenant_id', :t, true)"), {"t": str(ten_a_id)}
        )
        await conn.execute(
            text(
                "INSERT INTO memberships (id, tenant_id, user_id, role) VALUES (:m, :t, :u, 'owner') ON CONFLICT (tenant_id, user_id) DO NOTHING"
            ),
            {"m": mem_a_id, "t": ten_a_id, "u": sub_id},
        )
        access_a = f"{secret_sentinel}access_a_{secrets.token_urlsafe(24)}"
        refresh_a = f"{secret_sentinel}refresh_a_{secrets.token_urlsafe(24)}"
        for val, kind, exp in (
            (access_a, "access", now + timedelta(minutes=15)),
            (refresh_a, "refresh", now + timedelta(days=7)),
        ):
            d = hashlib.sha256(val.encode("utf-8")).hexdigest()
            await conn.execute(
                text(
                    "INSERT INTO oauth_tokens (token_digest, token_kind, client_id, subject_id, tenant_id, membership_id, credential_id, scopes, expires_at, family_id) VALUES (:d, :k, 'umcp-python-sdk', :u, :t, :m, :c, :s, :e, :f)"
                ),
                {
                    "d": d,
                    "k": kind,
                    "u": sub_id,
                    "t": ten_a_id,
                    "m": mem_a_id,
                    "c": uuid.uuid4(),
                    "s": scopes,
                    "e": exp,
                    "f": uuid.uuid4(),
                },
            )

        # Tenant B setup
        await conn.execute(
            text("INSERT INTO tenants (id, name) VALUES (:t, :n) ON CONFLICT (id) DO NOTHING"),
            {"t": ten_b_id, "n": f"staging-audit-b-{run_id}"},
        )
        await conn.execute(
            text("SELECT set_config('app.tenant_id', :t, true)"), {"t": str(ten_b_id)}
        )
        await conn.execute(
            text(
                "INSERT INTO memberships (id, tenant_id, user_id, role) VALUES (:m, :t, :u, 'owner') ON CONFLICT (tenant_id, user_id) DO NOTHING"
            ),
            {"m": mem_b_id, "t": ten_b_id, "u": sub_id},
        )
        access_b = f"{secret_sentinel}access_b_{secrets.token_urlsafe(24)}"
        refresh_b = f"{secret_sentinel}refresh_b_{secrets.token_urlsafe(24)}"
        for val, kind, exp in (
            (access_b, "access", now + timedelta(minutes=15)),
            (refresh_b, "refresh", now + timedelta(days=7)),
        ):
            d = hashlib.sha256(val.encode("utf-8")).hexdigest()
            await conn.execute(
                text(
                    "INSERT INTO oauth_tokens (token_digest, token_kind, client_id, subject_id, tenant_id, membership_id, credential_id, scopes, expires_at, family_id) VALUES (:d, :k, 'umcp-python-sdk', :u, :t, :m, :c, :s, :e, :f)"
                ),
                {
                    "d": d,
                    "k": kind,
                    "u": sub_id,
                    "t": ten_b_id,
                    "m": mem_b_id,
                    "c": uuid.uuid4(),
                    "s": scopes,
                    "e": exp,
                    "f": uuid.uuid4(),
                },
            )

        # C01 Authorization Code setup (binding challenge to authorized subject/tenant via oauth_states)
        state_val = f"{secret_sentinel}state_{secrets.token_urlsafe(24)}"
        state_d = hashlib.sha256(state_val.encode("utf-8")).hexdigest()
        code_d = hashlib.sha256(c01_auth_code.encode("utf-8")).hexdigest()
        await conn.execute(
            text(
                "INSERT INTO oauth_states (state_digest, client_id, redirect_uri, code_challenge, scopes, expires_at, client_state) VALUES (:sd, 'umcp-python-sdk', :ru, :ch, :s, :e, 'test-client-state')"
            ),
            {
                "sd": state_d,
                "ru": c01_redirect_uri,
                "ch": c01_challenge,
                "s": scopes,
                "e": now + timedelta(minutes=10),
            },
        )
        await conn.execute(
            text(
                "INSERT INTO oauth_authorization_codes (code_digest, state_digest, client_id, redirect_uri, subject_id, tenant_id, membership_id, credential_id, scopes, code_challenge, expires_at) VALUES (:cd, :sd, 'umcp-python-sdk', :ru, :u, :t, :m, :c, :s, :ch, :e)"
            ),
            {
                "cd": code_d,
                "sd": state_d,
                "ru": c01_redirect_uri,
                "u": sub_id,
                "t": ten_a_id,
                "m": mem_a_id,
                "c": uuid.uuid4(),
                "s": scopes,
                "ch": c01_challenge,
                "e": now + timedelta(minutes=10),
            },
        )

    try:
        negative_results = {name: "FAIL" for name in NEGATIVE_PROBES}
        if _unauthenticated_mcp_status(base_url) == 401:
            negative_results["unauthenticated_mcp_401"] = "PASS"

        # C01 authorization-code exchange and conformance run first.
        session_c01 = OAuthSession(
            base_url,
            client_id="umcp-python-sdk",
            redirect_uri=c01_redirect_uri,
            timeout=30.0,
        )
        session_c01.exchange_code(code=c01_auth_code, code_verifier=c01_verifier)
        try:
            session_c01.exchange_code(code=c01_auth_code, code_verifier=c01_verifier)
        except ProtocolError as exc:
            if exc.code == "invalid_grant":
                negative_results["authorization_code_replay_rejected"] = "PASS"

        transport_c01 = CloudOAuthTransport(session_c01)
        c01_checks = SDKConformanceRunner(transport_c01).run_all_checks()

        # C02 uses explicit synthetic pre-provisioned tokens; it is not login evidence.
        session_a = OAuthSession(base_url, client_id="umcp-python-sdk", timeout=30.0)
        session_a.set_tokens(
            TokenData(
                access_token=access_a,
                token_type="Bearer",
                expires_in=900,
                refresh_token=refresh_a,
                scope=" ".join(scopes),
            )
        )
        transport_a = CloudOAuthTransport(session_a)

        session_b = OAuthSession(base_url, client_id="umcp-python-sdk", timeout=30.0)
        session_b.set_tokens(
            TokenData(
                access_token=access_b,
                token_type="Bearer",
                expires_in=900,
                refresh_token=refresh_b,
                scope=" ".join(scopes),
            )
        )
        transport_b = CloudOAuthTransport(session_b)

        agent = ControlledMemoryAgent(transport_a, transport_b=transport_b)
        c02_report = agent.run_e2e_journey(
            audit_source_sha=audit_source_sha,
            audit_cycle_id=audit_cycle_id,
            server_source_sha=server_source_sha,
            server_digest=server_digest,
            server_revision=server_revision,
            audit_image_digest=audit_image_digest,
        )

        if (
            c01_checks["details"]
            .get("token_refresh_rotation", {})
            .get("old_refresh_rejected_status")
            == 400
        ):
            negative_results["old_refresh_rejected"] = "PASS"
        if c01_checks["details"].get("token_revocation", {}).get("post_revoke_status") == 401:
            negative_results["revoked_access_rejected_401"] = "PASS"
        if (
            c01_checks["details"].get("forged_authority_rejection", {}).get("server_rejected")
            is True
        ):
            negative_results["forged_authority_explicit_rejection"] = "PASS"
        denial_codes = (
            c02_report["step_details"].get("15_tenant_isolation", {}).get("explicit_denial_codes")
        )
        if isinstance(denial_codes, list) and len(denial_codes) == 2:
            negative_results["cross_tenant_explicit_rejection"] = "PASS"
        if c02_report["step_results"].get("9_tombstone_non_resurrection") == "PASS":
            negative_results["tombstone_non_resurrection"] = "PASS"

        c02_report["negative_results"] = dict(negative_results)
        c02_report["checksum"] = compute_canonical_checksum(c02_report)

        c01_report = generate_c01_report(
            base_url=base_url,
            audit_source_sha=audit_source_sha,
            audit_cycle_id=audit_cycle_id,
            negative_results=negative_results,
            server_source_sha=server_source_sha,
            server_digest=server_digest,
            server_revision=server_revision,
            audit_image_digest=audit_image_digest,
            transport_results=c01_checks["results"],
        )

        validate_c01_report(c01_report)
        validate_c02_report(c02_report)

        payload = {
            "audit_cycle_id": audit_cycle_id,
            "c01": c01_report,
            "c02": c02_report,
        }
        import json

        print("AUDIT_REPORTS_PAYLOAD:" + json.dumps(payload, separators=(",", ":")))
        return 0

    finally:
        async with engine.begin() as conn:
            # Delete tokens, codes and states specific to this run
            await conn.execute(
                text("DELETE FROM oauth_tokens WHERE tenant_id IN (:ta, :tb)"),
                {"ta": ten_a_id, "tb": ten_b_id},
            )
            await conn.execute(
                text("DELETE FROM oauth_authorization_codes WHERE tenant_id IN (:ta, :tb)"),
                {"ta": ten_a_id, "tb": ten_b_id},
            )
            await conn.execute(
                text("DELETE FROM oauth_states WHERE state_digest = :sd"), {"sd": state_d}
            )
            for t_id in (ten_a_id, ten_b_id):
                await conn.execute(
                    text("SELECT set_config('app.tenant_id', :t, true)"), {"t": str(t_id)}
                )
                await conn.execute(
                    text("DELETE FROM idempotency_operations WHERE tenant_id = :t"), {"t": t_id}
                )
                await conn.execute(
                    text("DELETE FROM memory_tombstones WHERE tenant_id = :t"), {"t": t_id}
                )
                await conn.execute(text("DELETE FROM memories WHERE tenant_id = :t"), {"t": t_id})
            await conn.execute(
                text("DELETE FROM memberships WHERE tenant_id IN (:ta, :tb)"),
                {"ta": ten_a_id, "tb": ten_b_id},
            )
            await conn.execute(
                text("DELETE FROM tenants WHERE id IN (:ta, :tb)"), {"ta": ten_a_id, "tb": ten_b_id}
            )
        await engine.dispose()


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except Exception as exc:
        detail = safe_error_detail(exc)
        print(
            f"AUDIT_FAIL:error_type={detail['error_type']},error_code={detail['error_code']}",
            file=sys.stderr,
        )
        sys.exit(1)
