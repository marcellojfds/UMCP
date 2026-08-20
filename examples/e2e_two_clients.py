"""Run the canonical journey through PostgreSQL and official MCP stdio.

Prerequisites: ``OMP_DATABASE_URL`` points to PostgreSQL with pgvector and
``alembic upgrade head`` has been run. This example intentionally has no demo
or file fallback.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime

from omp.sdk.client import MemoryClient, OfficialStdioTransport, ProtocolError


def provenance(source_type: str = "conversation") -> dict[str, str]:
    return {
        "source_type": source_type,
        "captured_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "source_id": "synthetic-mba",
    }


def main() -> None:
    database_url = os.environ.get("OMP_DATABASE_URL")
    if not database_url:
        raise SystemExit("OMP_DATABASE_URL is required; run migrations before this example")
    environment = dict(os.environ)
    environment["OMP_BACKEND"] = "postgres"
    client_a = MemoryClient(OfficialStdioTransport(env=environment))
    written = client_a.write(
        content=(
            "In an MBA context, marketplaces with local network effects should build "
            "geographic density before broad expansion."
        ),
        type="insight",
        owner_id="owner-a",
        provenance=provenance(),
        idempotency_key="mba-density-001",
    )
    memory_id = written["memory"]["id"]

    client_b = MemoryClient(OfficialStdioTransport(env=environment))
    positive = client_b.search(
        query="What should our GTM strategy do about geographic density and regional expansion?",
        owner_id="owner-a",
    )
    negative = client_b.search(query="unrelated recipe ingredients", owner_id="owner-a")
    try:
        client_b.update(
            id=memory_id,
            owner_id="owner-a",
            expected_version=99,
            patch={"importance": 0.9},
            provenance=provenance("agent"),
            idempotency_key="bad-version",
        )
    except ProtocolError as error:
        conflict = error.code
    else:
        conflict = "missing"
    updated = client_b.update(
        id=memory_id,
        owner_id="owner-a",
        expected_version=1,
        patch={"importance": 0.9},
        provenance=provenance("agent"),
        idempotency_key="good-version",
    )
    replay = client_b.update(
        id=memory_id,
        owner_id="owner-a",
        expected_version=1,
        patch={"importance": 0.9},
        provenance=provenance("agent"),
        idempotency_key="good-version",
    )
    forgotten = client_b.forget(id=memory_id, owner_id="owner-a", idempotency_key="forget-001")
    after = client_b.search(query="GTM regional expansion", owner_id="owner-a")
    print(
        {
            "positive_count": positive["count"],
            "negative_count": negative["count"],
            "conflict": conflict,
            "updated_version": updated["memory"]["version"],
            "replay_version": replay["memory"]["version"],
            "forget": forgotten["status"],
            "after_forget_count": after["count"],
        }
    )


if __name__ == "__main__":
    main()
