# Roadmap parallel bootstrap

**Status:** parallel lanes ready
**Baseline source:** `product/integration`
**Validated source SHA:** `5729c83e18cbd26c9ef759eaf7ff625a6060c6e1`
**Baseline branch/SHA:** `roadmap/baseline` at `325faf3`

## Branches and worktrees

| Branch | Worktree | Base SHA |
| --- | --- | --- |
| `roadmap/baseline` | `/private/tmp/umcp-roadmap-baseline` | `325faf3` |
| `roadmap/luna-core` | `/private/tmp/umcp-roadmap-core` | `325faf3` |
| `roadmap/luna-experience` | `/private/tmp/umcp-roadmap-experience` | `325faf3` |
| `roadmap/luna-verification` | `/private/tmp/umcp-roadmap-verification` | `325faf3` |
| `roadmap/integration` | `/private/tmp/umcp-roadmap-integration` | `325faf3` |

## Ownership

- `roadmap/luna-core`: Core/Data Plane owner — domain, application, PostgreSQL,
  MCP, cloud, server, migrations, gateway, worker, auth, RLS, crypto,
  persistence, backend contracts, and final milestone integration.
- `roadmap/luna-experience`: Luna B — `apps/web`, SDKs, and site/docs work,
  except for an integration conflict that must be resolved intentionally.
- `roadmap/luna-verification`: Luna C — verification, conformance, gates,
  demos, and independent evidence.
- `roadmap/integration`: controlled merge and acceptance branch; no milestone
  advances without capability, acceptance test, demo, current gates, and
  handoff.

## Initial gates

| Gate | Classification at bootstrap | Evidence |
| --- | --- | --- |
| HEAD/worktree/branch preflight | current | validated on source and all five new worktrees |
| `./scripts/gate-fast` | historical | last recorded on an earlier integration SHA |
| PostgreSQL zero→head / integration | historical | recorded in `INTEGRATION-RC.md`; rerun required |
| MCP stdio/HTTP conformance | historical | recorded in `INTEGRATION-RC.md`; rerun required |
| SDK and web tests/build/check | historical | recorded in `INTEGRATION-RC.md`; rerun required |
| auth negative, RLS, cross-tenant, crypto, tombstone/restore, workers | historical or not run | evidence must be refreshed on the active milestone SHA |
| browser E2E visual/keyboard/reduced-motion | not run | loopback/browser limitation recorded by post-mortem |
| holdout, deploy, push/PR/tag/release, real services/data | not run | explicitly outside local authorization |

The session post-mortem remains a partial historical record. This bootstrap is
not production-ready and does not issue an independent release `GO`.
