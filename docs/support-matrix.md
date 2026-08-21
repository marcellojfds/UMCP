# Support matrix

This matrix describes the conservative support boundary for the `0.1.0a1`
release candidate documentation. “Tested” means there is evidence in the
available handoffs or local checks; it does not imply a scale or security
guarantee.

| Area | Supported/tested | Not supported or not verified |
|---|---|---|
| Python | 3.11; CI and handoffs target it | Other Python versions are not verified |
| Database | PostgreSQL 16 with `pgvector`; migration head `0004_semantic_source_version` | SQLite, PostgreSQL without pgvector, and other major versions |
| MCP transport | Official Python MCP SDK over stdio; OMP contract `omp.mcp.v0` | HTTP MCP/Streamable HTTP; HTTP exposes only health/readiness when enabled |
| Backend | PostgreSQL is the release path; local file demo is explicit smoke-only | Demo/file backend as production or Gate B evidence |
| Embeddings | Local deterministic `hash/v1`, dimension 64; E5 and BGE semantic experiments are offline-only and NO-GO on frozen development quality | Semantic Gate B approval, BGE runtime integration, external-provider support, anonymity, or hosted inference |
| Client surface | Python SDK, CLI, and four MCP tools: write/search/update/forget | Other language SDKs, GUI, hosted API, or multi-tenant service |
| Operating system | Local Linux/macOS workflows observed; Docker is used for the disposable DB gate | Windows and production deployment topologies are not verified |
| Distribution | Planned GitHub Release only; package metadata is `open-memory-protocol==0.1.0a1` | PyPI publication in this release plan |

The Alpha trust model matters: in local stdio composition, `owner_id` is
provided by the client and trusted. It is a logical data partition, not
authentication or authorization. Memory content, provenance, exports,
backups, and embeddings are sensitive and readable by an operator with access
to the process, database, or files. See [`docs/privacy.md`](privacy.md) and
[`docs/threat-model.md`](threat-model.md).
