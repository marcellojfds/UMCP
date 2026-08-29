#!/usr/bin/env python3
"""Run one fail-closed C01→C02→containment cycle in authorized staging."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from omp.sdk.audit_contract import (  # noqa: E402
    C01_CAPABILITIES,
    C02_STEPS,
    DIGEST_RE,
    FULL_SHA_RE,
    NEGATIVE_PROBES,
    validate_c01_report,
    validate_c02_report,
)
from omp.sdk.checksums import compute_canonical_checksum  # noqa: E402

PROJECT = "umcp-mcp-staging-20260825"
REGION = "us-central1"
SERVICE = "umcp-cloud-staging"
RUNTIME_SA = f"umcp-runtime@{PROJECT}.iam.gserviceaccount.com"
VPC_CONNECTOR = "umcp-run-private"
EXPECTED_SERVER_SOURCE_SHA = "367cd365df43f9282f5155394cd39275169bf8f2"
EXPECTED_SERVER_DIGEST = "sha256:764263db4907ffbbbd50e77ab7d12e8d88cde2b5990a9879a40ddbd0976e4f1d"
EXPECTED_SERVER_REVISION = "umcp-cloud-staging-00018-f78"
AUDIT_IMAGE_PREFIX = f"{REGION}-docker.pkg.dev/{PROJECT}/umcp-docker-repo/umcp-audit@"
REPORT_NAMES = (
    "C01-SDK-RUNNER-REPORT-20260828.json",
    "C01-SDK-RUNNER-REPORT-20260828.md",
    "C02-CONTROLLED-AGENT-REPORT-20260828.json",
    "C02-CONTROLLED-AGENT-REPORT-20260828.md",
    "CONTAINMENT-REPORT-20260828.json",
    "CONTAINMENT-REPORT-20260828.md",
)


def _run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, capture_output=True, check=check)


def _validate_clean_source(source_sha: str) -> None:
    if not FULL_SHA_RE.fullmatch(source_sha):
        raise ValueError("audit source SHA must be a full lowercase Git SHA")
    head = _run(["git", "rev-parse", "HEAD"]).stdout.strip()
    dirty = _run(["git", "status", "--porcelain"]).stdout.strip()
    if head != source_sha or dirty:
        raise ValueError("audit source must equal the clean checkout HEAD")


def _validate_audit_image_uri(uri: str, source_sha: str) -> str:
    if not uri.startswith(AUDIT_IMAGE_PREFIX):
        raise ValueError("audit image is outside the authorized project/region/repository")
    digest = uri.removeprefix(AUDIT_IMAGE_PREFIX)
    if not DIGEST_RE.fullmatch(digest) or ":latest" in uri or "unknown" in uri:
        raise ValueError("audit image must use one immutable digest and no mutable tag")
    described = _run(
        [
            "gcloud",
            "artifacts",
            "docker",
            "images",
            "describe",
            uri,
            f"--project={PROJECT}",
            "--format=value(image_summary.digest)",
        ]
    ).stdout.strip()
    if described != digest:
        raise ValueError("Artifact Registry digest does not match the immutable URI")
    if not FULL_SHA_RE.fullmatch(source_sha):
        raise ValueError("audit image source SHA is malformed")
    return digest


def _discover_server() -> tuple[str, str, str]:
    raw = _run(
        [
            "gcloud",
            "run",
            "services",
            "describe",
            SERVICE,
            f"--project={PROJECT}",
            f"--region={REGION}",
            "--format=json(status.url,status.latestReadyRevisionName,spec.template.spec.containers[0].image)",
        ]
    ).stdout
    data = json.loads(raw)
    base_url = data.get("status", {}).get("url")
    revision = data.get("status", {}).get("latestReadyRevisionName")
    image = (
        data.get("spec", {})
        .get("template", {})
        .get("spec", {})
        .get("containers", [{}])[0]
        .get("image")
    )
    digest = image.split("@", 1)[1] if isinstance(image, str) and "@" in image else ""
    if base_url is None or not str(base_url).startswith("https://"):
        raise ValueError("staging service URL is missing or not HTTPS")
    if revision != EXPECTED_SERVER_REVISION or digest != EXPECTED_SERVER_DIGEST:
        raise ValueError("active server revision/digest diverges from H07 evidence")
    return str(base_url), str(revision), digest


def _read_execution_logs(job_name: str, execution_name: str) -> str:
    query = (
        f'resource.type="cloud_run_job" AND resource.labels.job_name="{job_name}" '
        f'AND labels."run.googleapis.com/execution_name"="{execution_name}"'
    )
    return _run(
        [
            "gcloud",
            "logging",
            "read",
            query,
            f"--project={PROJECT}",
            "--limit=200",
            "--order=asc",
            "--format=value(textPayload)",
        ]
    ).stdout


def _read_server_logs(started_at: str) -> str:
    query = (
        'resource.type="cloud_run_revision" '
        f'AND resource.labels.service_name="{SERVICE}" '
        f'AND resource.labels.revision_name="{EXPECTED_SERVER_REVISION}" '
        f'AND timestamp>="{started_at}"'
    )
    return _run(
        [
            "gcloud",
            "logging",
            "read",
            query,
            f"--project={PROJECT}",
            "--limit=300",
            "--order=asc",
            "--format=value(textPayload,jsonPayload.message,httpRequest.requestUrl)",
        ]
    ).stdout


def _delete_job(job_name: str) -> None:
    _run(
        [
            "gcloud",
            "run",
            "jobs",
            "delete",
            job_name,
            f"--project={PROJECT}",
            f"--region={REGION}",
            "--quiet",
        ],
        check=False,
    )


def _execute_audit_job(
    *,
    job_name: str,
    image_uri: str,
    cycle_id: str,
    base_url: str,
    source_sha: str,
    image_digest: str,
    server_revision: str,
    server_digest: str,
) -> tuple[str, dict[str, Any], str]:
    env_vars = ",".join(
        [
            f"UMCP_BASE_URL={base_url}",
            f"AUDIT_CYCLE_ID={cycle_id}",
            f"AUDIT_SOURCE_SHA={source_sha}",
            f"SERVER_SOURCE_SHA={EXPECTED_SERVER_SOURCE_SHA}",
            f"SERVER_DIGEST={server_digest}",
            f"SERVER_REVISION={server_revision}",
            f"AUDIT_IMAGE_DIGEST={image_digest}",
        ]
    )
    _delete_job(job_name)
    try:
        _run(
            [
                "gcloud",
                "run",
                "jobs",
                "create",
                job_name,
                f"--project={PROJECT}",
                f"--region={REGION}",
                f"--service-account={RUNTIME_SA}",
                f"--image={image_uri}",
                f"--vpc-connector={VPC_CONNECTOR}",
                "--vpc-egress=private-ranges-only",
                f"--set-env-vars={env_vars}",
                "--set-secrets=OMP_DATABASE_URL=umcp-database-url:1",
                "--command=python",
                "--args=-m,omp.sdk.audit_entrypoint",
                "--max-retries=0",
                "--task-timeout=20m",
            ]
        )
        execution_result = _run(
            [
                "gcloud",
                "run",
                "jobs",
                "execute",
                job_name,
                f"--project={PROJECT}",
                f"--region={REGION}",
                "--wait",
                "--format=value(metadata.name)",
            ],
            check=False,
        )
        execution = execution_result.stdout.strip()
        if not execution:
            raise ValueError("audit execution name is missing")
        logs = _read_execution_logs(job_name, execution)
        _scan_redaction(cycle_id, execution_result.stdout, execution_result.stderr, logs)
        if execution_result.returncode != 0:
            raise ValueError("audit execution failed")
        payload_lines = [
            line.removeprefix("AUDIT_REPORTS_PAYLOAD:")
            for line in logs.splitlines()
            if line.startswith("AUDIT_REPORTS_PAYLOAD:")
        ]
        if len(payload_lines) != 1:
            raise ValueError("audit execution did not emit one accepted payload")
        payload = json.loads(payload_lines[0])
        if payload.get("audit_cycle_id") != cycle_id:
            raise ValueError("audit payload cycle diverges from the requested cycle")
        return execution, payload, logs
    finally:
        _delete_job(job_name)


def _execute_containment_job(
    *, job_name: str, image_uri: str, cycle_id: str
) -> tuple[str, dict[str, int], str]:
    verifier = """import asyncio, os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
async def verify():
    engine = create_async_engine(os.environ['OMP_DATABASE_URL'])
    async with engine.begin() as conn:
        tokens = (await conn.execute(text("SELECT count(*) FROM oauth_tokens WHERE client_id = 'umcp-python-sdk'"))).scalar()
        codes = (await conn.execute(text("SELECT count(*) FROM oauth_authorization_codes WHERE client_id = 'umcp-python-sdk'"))).scalar()
        tenants = (await conn.execute(text("SELECT count(*) FROM tenants WHERE name LIKE 'staging-audit-%' OR name LIKE 'staging-test-%'"))).scalar()
    await engine.dispose()
    values = [tokens, codes, tenants]
    if any(type(value) is not int or value != 0 for value in values):
        raise SystemExit(1)
    print(f"CONTAINMENT_STATUS:{os.environ['AUDIT_CYCLE_ID']}:active_tokens={tokens},active_codes={codes},active_test_tenants={tenants}")
asyncio.run(verify())
"""
    encoded = base64.b64encode(verifier.encode()).decode()
    _delete_job(job_name)
    try:
        _run(
            [
                "gcloud",
                "run",
                "jobs",
                "create",
                job_name,
                f"--project={PROJECT}",
                f"--region={REGION}",
                f"--service-account={RUNTIME_SA}",
                f"--image={image_uri}",
                f"--vpc-connector={VPC_CONNECTOR}",
                "--vpc-egress=private-ranges-only",
                f"--set-env-vars=AUDIT_CYCLE_ID={cycle_id}",
                "--set-secrets=OMP_DATABASE_URL=umcp-database-url:1",
                "--command=python",
                f"--args=-c,import base64;exec(base64.b64decode('{encoded}').decode())",
                "--max-retries=0",
                "--task-timeout=10m",
            ]
        )
        execution_result = _run(
            [
                "gcloud",
                "run",
                "jobs",
                "execute",
                job_name,
                f"--project={PROJECT}",
                f"--region={REGION}",
                "--wait",
                "--format=value(metadata.name)",
            ],
            check=False,
        )
        execution = execution_result.stdout.strip()
        if not execution:
            raise ValueError("containment execution name is missing")
        logs = _read_execution_logs(job_name, execution)
        _scan_redaction(cycle_id, execution_result.stdout, execution_result.stderr, logs)
        if execution_result.returncode != 0:
            raise ValueError("containment execution failed")
        pattern = re.compile(
            rf"^CONTAINMENT_STATUS:{re.escape(cycle_id)}:active_tokens=(\d+),"
            rf"active_codes=(\d+),active_test_tenants=(\d+)$",
            re.MULTILINE,
        )
        matches = pattern.findall(logs)
        if len(matches) != 1:
            raise ValueError("containment did not emit one coherent metric map")
        values = tuple(int(value) for value in matches[0])
        if values != (0, 0, 0):
            raise ValueError("containment is not exact 0/0/0")
        keys = ("active_tokens", "active_codes", "active_test_tenants")
        return execution, dict(zip(keys, values, strict=True)), logs
    finally:
        _delete_job(job_name)


def _write_json(path: Path, payload: dict[str, Any]) -> str:
    payload["checksum"] = compute_canonical_checksum(payload)
    content = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    path.write_text(content, encoding="utf-8")
    return f"sha256:{hashlib.sha256(content.encode()).hexdigest()}"


def _common_md(report: dict[str, Any], file_name: str, file_sha: str) -> list[str]:
    provenance = report["provenance"]
    timestamp = report.get("created_at") or report.get("timestamp_utc")
    return [
        f"- **Data:** {timestamp}",
        f"- **Audit Cycle ID:** `{report['audit_cycle_id']}`",
        f"- **Base URL Staging:** `{report['base_url']}`",
        f"- **Audit Source SHA:** `{provenance['audit_source_sha']}`",
        f"- **Server Source SHA:** `{provenance['server_source_sha']}`",
        f"- **Server Image Digest:** `{provenance['server_digest']}`",
        f"- **Server Active Revision:** `{provenance['server_revision']}`",
        f"- **Audit Image Digest:** `{provenance['audit_image_digest']}`",
        f"- **Job Execution:** `{report['job_execution']}`",
        f"- **Report ID:** `{report['report_id']}`",
        f"- **Canonical JSON Artifact:** [`{file_name}`](./{file_name})",
        f"- **Checksum do Payload Canônico (SHA-256):** `{report['checksum']}`",
        f"- **Checksum do Arquivo JSON (SHA-256):** `{file_sha}`",
    ]


def _stage_reports(
    report_dir: Path,
    *,
    c01: dict[str, Any],
    c02: dict[str, Any],
    containment: dict[str, Any],
) -> None:
    c01_json = report_dir / REPORT_NAMES[0]
    c02_json = report_dir / REPORT_NAMES[2]
    containment_json = report_dir / REPORT_NAMES[4]
    c01_sha = _write_json(c01_json, c01)
    c02_sha = _write_json(c02_json, c02)
    containment_sha = _write_json(containment_json, containment)

    c01_lines = ["# C01 — Relatório de Conformance do SDK Python e Runner Comum", ""]
    c01_lines += _common_md(c01, c01_json.name, c01_sha)
    c01_lines += [
        "",
        "## Classificação OAuth",
        "",
        "A rodada comprovou uma troca authorization-code + PKCE com grant sintético pré-provisionado; não executou login interativo real.",
        "",
        "## Matriz C01",
        "",
        "| Capacidade | Status |",
        "| --- | --- |",
    ]
    c01_lines += [f"| `{name}` | **{c01['test_results'][name]}** |" for name in C01_CAPABILITIES]
    c01_lines += ["", "## Negativos", ""]
    c01_lines += [f"- `{name}`: **{c01['negative_results'][name]}**" for name in NEGATIVE_PROBES]
    (report_dir / REPORT_NAMES[1]).write_text("\n".join(c01_lines) + "\n", encoding="utf-8")

    c02_lines = ["# C02 — Relatório de Execução do Controlled Python Agent", ""]
    c02_lines += _common_md(c02, c02_json.name, c02_sha)
    c02_lines += [
        "",
        "## Classificação de credencial",
        "",
        "O agente usou tokens sintéticos pré-provisionados; o passo `2_oauth_pkce_login` não é evidência de login interativo real.",
        "A negação cross-tenant foi explícita na borda da aplicação; esta rodada não declara prova direta de RLS.",
        "",
        "## Jornada C02",
        "",
        "| Passo | Status |",
        "| --- | --- |",
    ]
    c02_lines += [f"| `{name}` | **{c02['step_results'][name]}** |" for name in C02_STEPS]
    c02_lines += ["", "## Negativos", ""]
    c02_lines += [f"- `{name}`: **{c02['negative_results'][name]}**" for name in NEGATIVE_PROBES]
    (report_dir / REPORT_NAMES[3]).write_text("\n".join(c02_lines) + "\n", encoding="utf-8")

    containment_lines = ["# Relatório de Contenção de Credenciais e Tenancy em Staging", ""]
    containment_lines += _common_md(containment, containment_json.name, containment_sha)
    containment_lines += ["", "## Métricas exatas", ""]
    containment_lines += [
        f"- **{name}:** `{containment['metrics'][name]}`"
        for name in ("active_tokens", "active_codes", "active_test_tenants")
    ]
    containment_lines += ["", "- **Status:** **PASS**"]
    (report_dir / REPORT_NAMES[5]).write_text("\n".join(containment_lines) + "\n", encoding="utf-8")


def _scan_redaction(cycle_id: str, *texts: str) -> None:
    sanitized_texts = [text.replace(RUNTIME_SA, "") for text in texts]
    patterns = (
        re.compile(re.escape(f"UMCPAUDIT_SECRET_{cycle_id}_")),
        re.compile(r"(?i)authorization\s*[:=]\s*bearer\s+\S+"),
        re.compile(r"(?i)postgres(?:ql)?(?:\+asyncpg)?://\S+"),
        re.compile(
            r"(?i)(?:client_secret|refresh_token|access_token|code_verifier)\s*[:=]\s*['\"]?[^\s,'\"]+"
        ),
        re.compile(r"(?i)[A-Za-z0-9._%+-]+@(?!.*gserviceaccount\.com)[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    )
    if any(pattern.search(text) for pattern in patterns for text in sanitized_texts):
        raise ValueError("redaction sentinel or forbidden secret-like value found")


def _promote_reports(stage: Path) -> None:
    target_dir = REPO_ROOT / "docs/handoffs/roadmap"
    for name in REPORT_NAMES:
        temporary = target_dir / f".{name}.w01r1-new"
        shutil.copyfile(stage / name, temporary)
        os.replace(temporary, target_dir / name)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-source-sha", required=True)
    parser.add_argument("--audit-image-uri", required=True)
    parser.add_argument(
        "--audit-cycle-id",
        default=f"audit-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}",
    )
    args = parser.parse_args()

    started_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    _validate_clean_source(args.audit_source_sha)
    image_digest = _validate_audit_image_uri(args.audit_image_uri, args.audit_source_sha)
    base_url, server_revision, server_digest = _discover_server()
    suffix = args.audit_cycle_id[-12:].replace("-", "")[:12]
    audit_job = f"umcp-c01c02-audit-{suffix}"
    containment_job = f"umcp-c01c02-cont-{suffix}"

    audit_execution, payload, audit_logs = _execute_audit_job(
        job_name=audit_job,
        image_uri=args.audit_image_uri,
        cycle_id=args.audit_cycle_id,
        base_url=base_url,
        source_sha=args.audit_source_sha,
        image_digest=image_digest,
        server_revision=server_revision,
        server_digest=server_digest,
    )
    c01 = payload.get("c01")
    c02 = payload.get("c02")
    if not isinstance(c01, dict) or not isinstance(c02, dict):
        raise ValueError("audit payload is missing C01 or C02")
    c01["job_execution"] = audit_execution
    c02["job_execution"] = audit_execution
    c01["checksum"] = compute_canonical_checksum(c01)
    c02["checksum"] = compute_canonical_checksum(c02)
    validate_c01_report(c01)
    print("C01_GATE: PASS 14/14 + negatives + provenance")
    validate_c02_report(c02)
    print("C02_GATE: PASS 15/15 + negatives + explicit cross-tenant denial")

    containment_execution, metrics, containment_logs = _execute_containment_job(
        job_name=containment_job,
        image_uri=args.audit_image_uri,
        cycle_id=args.audit_cycle_id,
    )
    containment = {
        "report_id": f"containment-{args.audit_cycle_id}",
        "audit_cycle_id": args.audit_cycle_id,
        "timestamp_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "base_url": base_url,
        "provenance": dict(c01["provenance"]),
        "job_execution": containment_execution,
        "metrics": metrics,
        "status": "PASS",
    }

    with tempfile.TemporaryDirectory(prefix="umcp-w01r1-") as temp_dir:
        stage = Path(temp_dir)
        _stage_reports(stage, c01=c01, c02=c02, containment=containment)
        artifacts = "\n".join((stage / name).read_text(encoding="utf-8") for name in REPORT_NAMES)
        server_logs = _read_server_logs(started_at)
        _scan_redaction(
            args.audit_cycle_id,
            audit_logs,
            containment_logs,
            server_logs,
            artifacts,
        )
        verification = _run(
            [
                sys.executable,
                "-S",
                str(REPO_ROOT / "scripts/verify_checksums.py"),
                "--report-dir",
                str(stage),
            ],
            check=False,
        )
        if verification.returncode != 0:
            raise ValueError("stdlib-only staged report verification failed")
        _promote_reports(stage)

    print("CONTAINMENT_GATE: PASS 0/0/0")
    print("REDACTION_GATE: PASS sentinel/log/artifact scan")
    print(f"AUDIT_CYCLE_ID: {args.audit_cycle_id}")
    print(f"AUDIT_EXECUTION: {audit_execution}")
    print(f"CONTAINMENT_EXECUTION: {containment_execution}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        print(f"AUDIT_WRAPPER_FAIL:{exc.__class__.__name__}", file=sys.stderr)
        sys.exit(1)
