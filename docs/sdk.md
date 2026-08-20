# Python SDK

The SDK is a thin client over the MCP contract. It does not access PostgreSQL
directly or reimplement domain rules.

```python
import os

from omp.sdk import MemoryClient, OfficialStdioTransport

environment = dict(os.environ)
environment["OMP_BACKEND"] = "postgres"
client = MemoryClient(OfficialStdioTransport(env=environment))

created = client.write(
    owner_id="example-owner",
    content="Synthetic example: ship the beta after the migration rehearsal.",
    type="decision",
    provenance={
        "source_type": "system",
        "captured_at": "2026-01-01T12:00:00Z",
    },
    idempotency_key="example-write-1",
)
result = client.search(
    owner_id="example-owner",
    query="What is the beta release decision?",
    limit=5,
)
print(created["status"], result["count"])
```

Set `OMP_DATABASE_URL` in the environment and apply migrations before running
the example. `OfficialStdioTransport` starts a fresh local server process for
each call. `ProtocolError` exposes the stable public error code and a
retryable flag; messages are intended to avoid payload and secret leakage.

For export/import, use the local administrative transport through
`client.export(path, owner_id=...)` and `client.import_file(path,
dry_run=True)`. Exports are owner-scoped, omit embeddings by default, and are
still sensitive files. Supplying embeddings is an explicit sensitive choice;
forgetting a database record does not revoke an existing export or backup.

The runnable PostgreSQL examples are
[`examples/mcp_stdio_client.py`](../examples/mcp_stdio_client.py) and
[`examples/e2e_two_clients.py`](../examples/e2e_two_clients.py).
