# UMCP — Open Memory Protocol

UMCP is a user-owned memory layer for AI assistants. It gives a signed-in user
one durable memory vault that can be reached through MCP from different model
surfaces, while keeping identity, lifecycle, provenance, and deletion under
server control.

## Current status

UMCP is a **private staging MVP**, not a production service or public release.
The current deployed path has been exercised with one maintainer account:

- Google OAuth establishes the UMCP owner server-side;
- ChatGPT can connect to the hosted Streamable HTTP MCP and save memory;
- Gemini can connect as a custom app in **Gemini Spark** and read the same
  owner's memory;
- the UMCP portal displays memories stored for the signed-in owner; and
- PostgreSQL/pgvector, tenant scoping, OAuth token ledgers, and the hosted MCP
  boundary are implemented in the staging line.

The cross-surface MVP was verified on 2026-08-30: Gemini retrieved the exact
preference `A cor favorita de Marcello é roxo.` from UMCP. The deployed source
for that verification is `1233b221fd89edb1691bd6bd09c2d21eee4822bf`.

The MVP still has an important retrieval defect: the default
`min_relevance=0.78` can hide a relevant result. The verified Gemini lookup
required `min_relevance=0.0`. Fixing and recalibrating retrieval is the first
product priority; see [Current state](docs/CURRENT_STATE.md) and
[Known issues](docs/known-issues.md).

## Hosted staging

- Landing and portal:
  `https://umcp-cloud-staging-yqjlathj7q-uc.a.run.app/portal/`
- MCP endpoint:
  `https://umcp-cloud-staging-yqjlathj7q-uc.a.run.app/mcp`
- Health:
  `https://umcp-cloud-staging-yqjlathj7q-uc.a.run.app/healthz`

Staging is restricted to the allowlisted test identity. Do not treat these
URLs as a public beta invitation or production SLA.

## Hosted tools

The authenticated Cloud MCP exposes:

- `memory.write`
- `memory.search`
- `memory.capture`
- `memory.update`
- `memory.forget`

Hosted callers never supply `owner_id` or `tenant_id`. UMCP derives both from
the verified OAuth principal. The local Community/stdio interface remains a
separate compatibility path where `owner_id` is caller-provided and must not
be exposed to untrusted users.

## Local development

Requires Python 3.11 and Docker:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
./scripts/gate-fast
./scripts/gate-postgres
```

The PostgreSQL gate uses a disposable PostgreSQL 16 + pgvector environment.
The file-backed backend is a demo fixture only.

## Documentation

Start with the [documentation index](docs/README.md):

- [Current deployed state](docs/CURRENT_STATE.md)
- [Installation and connection](docs/installation.md)
- [MCP contract](docs/mcp.md)
- [Compatibility matrix](docs/support-matrix.md)
- [Known issues](docs/known-issues.md)
- [Roadmap](docs/roadmap.md)
- [Privacy](docs/privacy.md) and [hosted threat model](docs/threat-model-hosted-v1.md)

ADRs, handoffs, evaluation reports, old gameplans, and workstream plans are
historical evidence. They are not current status unless the documentation
index explicitly promotes them.

## Project policy

Read [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), and the
[Code of Conduct](CODE_OF_CONDUCT.md). The project is licensed under
[Apache-2.0](LICENSE).
