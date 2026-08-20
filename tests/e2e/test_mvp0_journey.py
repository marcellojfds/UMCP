"""Gate B journey through a real server process and the official MCP client.

The test is intentionally skipped when no PostgreSQL URL is supplied so local
contract runs remain fast. ``OMP_REQUIRE_POSTGRES_TESTS=1`` turns that skip
into a failure and is the CI/release setting.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import uuid
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from omp.sdk.client import MemoryClient, OfficialStdioTransport, ProtocolError


def _database_url() -> str:
    value = os.environ.get("OMP_TEST_DATABASE_URL") or os.environ.get("OMP_DATABASE_URL")
    if not value:
        if os.environ.get("OMP_REQUIRE_POSTGRES_TESTS") == "1":
            pytest.fail("OMP_REQUIRE_POSTGRES_TESTS=1 but OMP_TEST_DATABASE_URL is unset")
        pytest.skip("PostgreSQL E2E requires OMP_TEST_DATABASE_URL")
    return value


def _apply_migrations(root: Path, database_url: str) -> None:
    environment = dict(os.environ)
    environment.update(
        {
            "OMP_DATABASE_URL": database_url,
            "OMP_BACKEND": "postgres",
            "PYTHONPATH": str(root / "src"),
        }
    )
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=root,
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if result.returncode != 0:
        pytest.fail("PostgreSQL migrations could not be applied")


def _client(database_url: str, log_path: Path) -> MemoryClient:
    environment = dict(os.environ)
    environment.update({"OMP_DATABASE_URL": database_url, "OMP_BACKEND": "postgres"})
    return MemoryClient(OfficialStdioTransport(env=environment, log_path=log_path))


def _provenance(source_type: str = "conversation") -> dict[str, str]:
    return {
        "source_type": source_type,
        "captured_at": "2026-01-01T12:00:00Z",
        "source_id": "synthetic-mba",
    }


async def _cascade_counts(database_url: str, memory_id: str) -> dict[str, int]:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            values: dict[str, int] = {}
            for table in ("memory_versions", "memory_embeddings"):
                result = await connection.execute(
                    text(f"SELECT count(*) FROM {table} WHERE memory_id = :memory_id"),
                    {"memory_id": memory_id},
                )
                values[table] = int(result.scalar_one())
            relation_result = await connection.execute(
                text(
                    "SELECT count(*) FROM memory_relations "
                    "WHERE source_id = :memory_id OR target_id = :memory_id"
                ),
                {"memory_id": memory_id},
            )
            values["memory_relations"] = int(relation_result.scalar_one())
            return values
    finally:
        await engine.dispose()


def test_mvp0_journey_postgres_official_stdio(tmp_path: Path) -> None:
    database_url = _database_url()
    root = Path(__file__).resolve().parents[2]
    _apply_migrations(root, database_url)
    log_path = tmp_path / "server.log"
    client_a = _client(database_url, log_path)
    canary = "CANARY-MBA-DENSITY-DO-NOT-LOG"
    run_id = uuid.uuid4().hex[:10]
    owner_a = f"owner-a-{run_id}"
    owner_b = f"owner-b-{run_id}"
    write_key = f"mba-density-{run_id}"

    written = client_a.write(
        content=(
            "In an MBA context, the GTM strategy question is: What GTM strategy "
            "follows the MBA lesson: geographic density before broad geographic "
            f"expansion? Answer: prioritize geographic density before broad geographic "
            f"expansion. {canary}"
        ),
        type="insight",
        owner_id=owner_a,
        provenance=_provenance(),
        idempotency_key=write_key,
    )
    memory_id = written["memory"]["id"]

    # A fresh official client starts a fresh real server process.
    client_b = _client(database_url, log_path)
    positive = client_b.search(
        query=(
            "What GTM strategy follows the MBA lesson: geographic density before broad "
            "geographic expansion?"
        ),
        owner_id=owner_a,
        limit=5,
        min_relevance=0.78,
    )
    assert positive["count"] == 1
    assert positive["memories"][0]["reason_retrieved"]
    assert client_b.search(query="unrelated recipe ingredients", owner_id=owner_a)["count"] == 0
    assert client_b.search(query="geographic density", owner_id=owner_b)["count"] == 0

    with pytest.raises(ProtocolError) as cross_owner:
        client_b.update(
            id=memory_id,
            owner_id=owner_b,
            expected_version=1,
            patch={"importance": 0.9},
            provenance=_provenance("agent"),
            idempotency_key="cross-owner",
        )
    assert cross_owner.value.code == "not_found"

    with pytest.raises(ProtocolError) as stale:
        client_b.update(
            id=memory_id,
            owner_id=owner_a,
            expected_version=99,
            patch={"importance": 0.9},
            provenance=_provenance("agent"),
            idempotency_key="stale-version",
        )
    assert stale.value.code == "version_conflict"

    update_args = {
        "id": memory_id,
        "owner_id": owner_a,
        "expected_version": 1,
        "patch": {"importance": 0.9},
        "provenance": _provenance("agent"),
        "idempotency_key": "good-version",
    }
    updated = client_b.update(**update_args)
    assert updated["memory"]["version"] == 2
    replay = client_b.update(**update_args)
    assert replay["memory"]["version"] == 2

    with pytest.raises(ProtocolError) as idempotency_conflict:
        client_b.update(
            **{
                **update_args,
                "patch": {"importance": 0.8},
            }
        )
    assert idempotency_conflict.value.code == "validation_error"

    export_path = tmp_path / "mvp0-export.json"
    exported = client_b.export(export_path, owner_id=owner_a)
    assert exported.format == "omp.export.v0"
    export_payload = export_path.read_text(encoding="utf-8")
    assert '"includes_embeddings": false' in export_payload
    assert "embedding_values" not in export_payload
    assert "history" in export_payload

    forgotten = client_b.forget(
        id=memory_id,
        owner_id=owner_a,
        idempotency_key="forget-001",
    )
    assert forgotten["status"] == "forgotten"
    assert (
        client_b.forget(id=memory_id, owner_id=owner_a, idempotency_key="forget-001")["status"]
        == "already_absent"
    )
    assert client_b.search(query="geographic density GTM", owner_id=owner_a)["count"] == 0

    cascade = asyncio.run(_cascade_counts(database_url, memory_id))
    assert cascade == {"memory_versions": 0, "memory_embeddings": 0, "memory_relations": 0}

    assert client_b.import_file(export_path, dry_run=True)["count"] == 0
    assert client_b.import_file(export_path)["count"] == 1
    assert client_b.import_file(export_path)["count"] == 0
    assert (
        client_b.search(
            query=(
                "What GTM strategy follows the MBA lesson: geographic density before broad "
                "geographic expansion?"
            ),
            owner_id=owner_a,
        )["count"]
        == 1
    )
    assert (
        client_b.forget(id=memory_id, owner_id=owner_a, idempotency_key="forget-002")["status"]
        == "forgotten"
    )
    assert canary not in log_path.read_text(encoding="utf-8")
