# M0 — Verification handoff

Status: `complete-with-external-findings`

This is a Verification handoff, not an independent release GO.

## Candidate and acceptance

- Worktree: `/private/tmp/umcp-roadmap-verification`
- Branch: `roadmap/luna-verification`
- Tested executable SHA for the latest gate-fast run: `2c305ed1d339bec1252a087df60d38e2741235c7`
- Acceptance command: `./scripts/gate-fast` and `./scripts/gate-postgres`
- Demo command: `scripts/demo-local-integration`
- Data boundary: synthetic/disposable only; no holdout, real user, secret,
  email, paid service or external deployment.

## Gate freshness

See [`GATE-FRESHNESS.json`](GATE-FRESHNESS.json) and its rendered table from
`scripts/check-gate-freshness`. The executable gates listed as current were run
on the SHA above. Historical evidence remains historical.

## Results

### Current gates

- gate-fast: environment-blocked; lint/mypy + 71 tests passed, while two HTTP
  MCP contract tests could not bind a loopback socket.
- PostgreSQL/migrations: pass, 19 tests; PostgreSQL 16.15 + pgvector 0.8.6;
  zero-to-head and downgrade/re-upgrade reached `0007_tenant_fks`.
- SDK: pass, 2 tests. Web: pass, check + 3 tests + build.
- secret/PII, dependency vulnerability, SBOM, local links/claims: pass.

### Historical gates

The integration post-mortem's older SDK, web, conformance, security and worker
results remain historical unless repeated above. They are not promoted by this
handoff.

### Failures and findings

- [`M0-ENV-001.md`](findings/M0-ENV-001.md): managed browser unavailable.
- [`M0-ENV-002.md`](findings/M0-ENV-002.md): loopback socket binding unavailable;
  HTTP MCP contract tests remain environment-blocked.
- No implementation finding was invented because no integrated Core candidate
  was delivered to this lane.

### Environment blockers

The browser smoke was attempted through the managed browser runtime and found
zero connected backends. Browser E2E is `environment-blocked`, never `pass`.
The HTTP MCP smoke was attempted by the contract tests and was blocked before
server startup by the sandbox's loopback socket restriction.

## Artifacts and checksums

See [`evidence/`](evidence/) and `evidence/checksums.sha256`.

## Technical recommendation

Keep this verification harness and gates as the independent baseline. Wait for
the integration lane to publish `M1-INTEGRATED.md`, then rerun affected gates
against that candidate. Do not issue a release GO.

## Synchronization

- Required integration handoff: `docs/handoffs/roadmap/M1-INTEGRATED.md`
- Next candidate SHA: not available; handoff not present.
