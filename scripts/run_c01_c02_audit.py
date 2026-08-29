#!/usr/bin/env python3
"""Versioned entrypoint for running C01 Conformance and C02 Controlled Agent audits."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

# Add src to sys.path
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root / "src"))

from omp.sdk.agent import ControlledMemoryAgent
from omp.sdk.cloud import CloudOAuthTransport
from omp.sdk.oauth import OAuthSession, TokenData
from omp.sdk.runner import SDKConformanceRunner, generate_c01_report


def issue_two_test_sessions() -> tuple[dict[str, Any], dict[str, Any]]:
    """Issue two independent test sessions in staging for Tenant A and Tenant B."""
    py_code = """
import asyncio, hashlib, json, os, secrets, uuid
from datetime import datetime, UTC, timedelta
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

async def run():
    engine = create_async_engine(os.environ['OMP_DATABASE_URL'])
    run_id = secrets.token_hex(4)
    sessions = []
    scopes = ['memory:read', 'memory:write', 'memory:delete']
    now = datetime.now(UTC)
    async with engine.begin() as conn:
        for tag in ('tenant-a', 'tenant-b'):
            subject = f'audit-{tag}-{run_id}'
            sub_id = uuid.uuid5(uuid.NAMESPACE_URL, 'umcp/test/user/' + subject)
            ten_id = uuid.uuid5(uuid.NAMESPACE_URL, 'umcp/test/tenant/' + subject)
            mem_id = uuid.uuid5(uuid.NAMESPACE_URL, 'umcp/test/membership/' + subject)
            cred_id = uuid.uuid4()
            family_id = uuid.uuid4()
            access = f'at_{tag}_' + secrets.token_urlsafe(32)
            refresh = f'rt_{tag}_' + secrets.token_urlsafe(32)
            await conn.execute(text("INSERT INTO tenants (id, name) VALUES (:t, :n) ON CONFLICT (id) DO NOTHING"), {'t': ten_id, 'n': f'staging-audit-{tag}'})
            await conn.execute(text("INSERT INTO users (id) VALUES (:u) ON CONFLICT (id) DO NOTHING"), {'u': sub_id})
            await conn.execute(text("SELECT set_config('app.tenant_id', :t, true)"), {'t': str(ten_id)})
            await conn.execute(text("INSERT INTO memberships (id, tenant_id, user_id, role) VALUES (:m, :t, :u, 'owner') ON CONFLICT (tenant_id, user_id) DO NOTHING"), {'m': mem_id, 't': ten_id, 'u': sub_id})
            for val, kind, exp in ((access, 'access', now + timedelta(minutes=15)), (refresh, 'refresh', now + timedelta(days=7))):
                digest = hashlib.sha256(val.encode('utf-8')).hexdigest()
                await conn.execute(text("INSERT INTO oauth_tokens (token_digest, token_kind, client_id, subject_id, tenant_id, membership_id, credential_id, scopes, expires_at, family_id) VALUES (:d, :k, 'umcp-python-sdk', :u, :t, :m, :c, :s, :e, :f)"), {'d': digest, 'k': kind, 'u': sub_id, 't': ten_id, 'm': mem_id, 'c': cred_id, 's': scopes, 'e': exp, 'f': family_id})
            sessions.append({'access_token': access, 'refresh_token': refresh, 'token_type': 'Bearer', 'expires_in': 900, 'scope': ' '.join(scopes)})
    await engine.dispose()
    print('AUDIT_SESSIONS_PAYLOAD:' + json.dumps(sessions))

asyncio.run(run())
"""
    import base64
    b64_script = base64.b64encode(py_code.encode("utf-8")).decode("ascii")

    job_name = "umcp-h07-issue-test-session"
    subprocess.run(
        [
            "gcloud", "run", "jobs", "delete", job_name,
            "--region", "us-central1", "--quiet",
        ],
        capture_output=True,
        check=False,
    )
    subprocess.run(
        [
            "gcloud", "run", "jobs", "create", job_name,
            "--region", "us-central1",
            "--service-account=umcp-runtime@umcp-mcp-staging-20260825.iam.gserviceaccount.com",
            "--image=southamerica-east1-docker.pkg.dev/umcp-mcp-staging-20260825/umcp-docker-repo/umcp@sha256:764263db4907ffbbbd50e77ab7d12e8d88cde2b5990a9879a40ddbd0976e4f1d",
            "--vpc-connector=umcp-run-private",
            "--vpc-egress=private-ranges-only",
            "--set-secrets=OMP_DATABASE_URL=umcp-database-url:1",
            "--command=python",
            f"--args=-c,import base64; exec(base64.b64decode('{b64_script}').decode())",
        ],
        check=True,
    )
    exec_out = subprocess.check_output(
        ["gcloud", "run", "jobs", "execute", job_name, "--region", "us-central1", "--wait", "--format=value(metadata.name)"],
    ).decode("utf-8").strip()

    log_cmd = [
        "gcloud", "logging", "read",
        f'resource.type="cloud_run_job" AND resource.labels.job_name="{job_name}" AND labels."run.googleapis.com/execution_name"="{exec_out}" AND textPayload=~"^AUDIT_SESSIONS_PAYLOAD:"',
        "--project", "umcp-mcp-staging-20260825",
        "--limit", "1",
        "--format=value(textPayload)",
    ]
    out = subprocess.check_output(log_cmd).decode("utf-8").strip()
    subprocess.run(["gcloud", "run", "jobs", "delete", job_name, "--region", "us-central1", "--quiet"], capture_output=True, check=False)

    if not out.startswith("AUDIT_SESSIONS_PAYLOAD:"):
        raise RuntimeError(f"Failed to extract AUDIT_SESSIONS_PAYLOAD from execution {exec_out}")

    payload = json.loads(out[len("AUDIT_SESSIONS_PAYLOAD:"):])
    return payload[0], payload[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run C01 and C02 audit journeys against staging")
    parser.add_argument("--base-url", default="https://umcp-cloud-staging-yqjlathj7q-uc.a.run.app")
    parser.add_argument("--server-sha", default="367cd365df43f9282f5155394cd39275169bf8f2")
    parser.add_argument("--server-digest", default="sha256:764263db4907ffbbbd50e77ab7d12e8d88cde2b5990a9879a40ddbd0976e4f1d")
    parser.add_argument("--server-revision", default="umcp-cloud-staging-00018-f78")
    args = parser.parse_args()

    print("[*] Issuing independent sessions for Tenant A and Tenant B...")
    session_data_a, session_data_b = issue_two_test_sessions()

    # Session A for C01 & C02 Primary
    session_a = OAuthSession(args.base_url, client_id="umcp-python-sdk")
    session_a.set_tokens(TokenData(
        access_token=session_data_a["access_token"],
        token_type=session_data_a["token_type"],
        expires_in=session_data_a["expires_in"],
        refresh_token=session_data_a.get("refresh_token"),
        scope=session_data_a.get("scope", ""),
    ))
    transport_a = CloudOAuthTransport(session_a)

    # Session B for C02 Cross-Tenant Isolation
    session_b = OAuthSession(args.base_url, client_id="umcp-python-sdk")
    session_b.set_tokens(TokenData(
        access_token=session_data_b["access_token"],
        token_type=session_data_b["token_type"],
        expires_in=session_data_b["expires_in"],
        refresh_token=session_data_b.get("refresh_token"),
        scope=session_data_b.get("scope", ""),
    ))
    transport_b = CloudOAuthTransport(session_b)

    # Run C02 Controlled Agent Journey First (requires active tokens for write/recall/isolation before refresh/revoke)
    print("\n[*] Running C02 Controlled Memory Agent Journey (15 steps)...")
    agent = ControlledMemoryAgent(transport_a, transport_b=transport_b)
    c02_json_path = repo_root / "docs/handoffs/roadmap/C02-CONTROLLED-AGENT-REPORT-20260828.json"
    c02_md_path = repo_root / "docs/handoffs/roadmap/C02-CONTROLLED-AGENT-REPORT-20260828.md"
    c02_report = agent.run_e2e_journey(
        server_sha=args.server_sha,
        server_digest=args.server_digest,
        server_revision=args.server_revision,
        output_json_path=c02_json_path,
        output_md_path=c02_md_path,
    )

    print("\n--- C02 Step Results ---")
    for step, status in c02_report["step_results"].items():
        print(f"  {step}: {status}")
    print(f"C02 Total: {c02_report['summary']['passed_steps']}/{c02_report['summary']['total_steps']} PASS")
    print(f"C02 Payload Checksum: {c02_report['checksum']}")
    print(f"C02 File Checksum:    {c02_report['file_sha256']}")

    # Issue fresh Session for C01 Conformance Runner
    print("\n[*] Issuing fresh session for C01 Conformance Runner...")
    c01_session_data, _ = issue_two_test_sessions()
    session_c01 = OAuthSession(args.base_url, client_id="umcp-python-sdk")
    session_c01.set_tokens(TokenData(
        access_token=c01_session_data["access_token"],
        token_type=c01_session_data["token_type"],
        expires_in=c01_session_data["expires_in"],
        refresh_token=c01_session_data.get("refresh_token"),
        scope=c01_session_data.get("scope", ""),
    ))
    transport_c01 = CloudOAuthTransport(session_c01)

    print("[*] Running C01 SDK Conformance Runner (14 capabilities)...")
    runner = SDKConformanceRunner(transport_c01)
    runner_checks = runner.run_all_checks()

    c01_json_path = repo_root / "docs/handoffs/roadmap/C01-SDK-RUNNER-REPORT-20260828.json"
    c01_md_path = repo_root / "docs/handoffs/roadmap/C01-SDK-RUNNER-REPORT-20260828.md"
    c01_report = generate_c01_report(
        base_url=args.base_url,
        server_sha=args.server_sha,
        server_digest=args.server_digest,
        server_revision=args.server_revision,
        transport_results=runner_checks["results"],
        output_json_path=c01_json_path,
        output_md_path=c01_md_path,
    )

    print("\n--- C01 Capability Results ---")
    for cap, status in runner_checks["results"].items():
        print(f"  {cap}: {status}")
    print(f"C01 Total: {c01_report['summary']['supported_count']}/{c01_report['summary']['total_capabilities']} Supported")
    print(f"C01 Payload Checksum: {c01_report['checksum']}")
    print(f"C01 File Checksum:    {c01_report['file_sha256']}")

    if c02_report["summary"]["failed_steps"] > 0 or c01_report["summary"]["unverified_count"] > 0:
        print("\n[!] AUDIT FAILED: Non-zero failures detected.", file=sys.stderr)
        return 1

    print("\n[+] ALL AUDIT JOURNEYS COMPLETED WITH ZERO FAILURES.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
