"""Minimal SDK client example using PostgreSQL and official MCP stdio."""

from __future__ import annotations

import os

from omp.sdk.client import MemoryClient, OfficialStdioTransport


def main() -> None:
    if not os.environ.get("OMP_DATABASE_URL"):
        raise SystemExit(
            "OMP_DATABASE_URL is required; apply migrations before running this example"
        )
    environment = dict(os.environ)
    environment["OMP_BACKEND"] = "postgres"
    client = MemoryClient(OfficialStdioTransport(env=environment))
    result = client.search(query="GTM strategy", owner_id="example-owner", limit=5)
    print({"count": result["count"], "protocol": "omp.mcp.v0"})


if __name__ == "__main__":
    main()
