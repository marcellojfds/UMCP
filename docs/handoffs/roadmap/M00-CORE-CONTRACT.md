# M00 Core milestone contract

**Branch:** `roadmap/luna-core`
**Worktree:** `/private/tmp/umcp-roadmap-core`
**Base:** `325faf3` (from validated `product/integration` `5729c83`)
**Status:** frozen before implementation

## Capability

The local integration candidate can be exercised through one deterministic,
synthetic demo that proves its current MCP/application path and reports which
evidence is current versus historical. It remains a local candidate, not a
production or release claim.

## Acceptance test and demo

```sh
./scripts/demo-local-integration
```

The same entrypoint accepts an integration context after the controlled merge:

```sh
./scripts/demo-local-integration roadmap/integration /private/tmp/umcp-roadmap-integration
```

The command must exit zero, verify its branch/worktree/SHA, use disposable
synthetic tenant data, complete write → search → update → forget, verify the
forgotten item is absent, and reject a forged owner/tenant access attempt. It
must print no plaintext secrets and must identify external/unsupported gates as
`not run` or `environment-blocked`.

## Owned paths

- `scripts/demo-local-integration`
- `scripts/assert-worktree-context`
- `scripts/assert-m00-handoffs`
- `scripts/gate-postgres` (G00 gate reliability fix)
- `GOAL-PROGRESS.md`
- `docs/handoffs/roadmap/M00-CORE-DONE.md`

No `apps/web`, SDK, or site files are in scope for Core M00.

## Gates

Current gates will be run on the final M00 SHA. Earlier results in the
post-mortem and `INTEGRATION-RC.md` remain historical unless rerun unchanged on
that SHA. M00 cannot claim independent release `GO`.
