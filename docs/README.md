# UMCP documentation

This index defines which documents describe the product **now**. If an older
plan or handoff conflicts with this index, the current-state documents and the
executable code win.

## Current sources of truth

1. [Current deployed state](CURRENT_STATE.md)
2. [Roadmap](roadmap.md)
3. [Known issues](known-issues.md)
4. [Compatibility matrix](support-matrix.md)
5. [Installation and connection](installation.md)
6. [MCP contract](mcp.md)
7. [Hosted threat model](threat-model-hosted-v1.md) and [privacy policy](privacy.md)

## Stable technical references

- [Protocol reference](protocol.md)
- [Memory model](memory-model.md)
- [Python SDK](sdk.md) and [CLI](cli.md)
- [ADRs](adr/)
- [MCP schemas](contracts/mcp/)
- [Runbooks](runbooks/)

## Historical evidence — not current status

The following directories and files are intentionally retained for audit and
decision history. Dates, blockers, branch names, and “active” labels inside
them describe their original session only:

- `docs/handoffs/`
- `evals/reports/`
- `docs/work-journal/`
- `docs/workstreams/`
- `docs/execution/mcp-readiness/`
- `docs/*GAMEPLAN*.md`
- `docs/DELIVERY_GAMEPLAN.md`
- `docs/EXECUTION_PLAN_QA_RELEASE.md`
- `docs/CODEX_DELIVERY_ROADMAP.md`
- `docs/roadmap_implementation.md`

Do not resume work, publish a support claim, or infer the deployed revision
from a historical file. Use [Current state](CURRENT_STATE.md).

## Documentation maintenance rule

Every behavior or support claim must be one of:

- **verified** — exercised on a named surface/date/SHA;
- **implemented** — present in code and tests but not accepted on that surface;
- **experimental** — available without a support commitment; or
- **planned** — roadmap only.

Never use “supported”, “secure”, “works everywhere”, or “production-ready”
without the corresponding evidence and scope.
