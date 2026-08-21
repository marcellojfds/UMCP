# M00 Integrated Handoff

## Status

M00 is integrated locally on `roadmap/integration`. This is an integration
handoff, not an independent audit and not a release GO.

- integration worktree: `/private/tmp/umcp-roadmap-integration`
- tested code HEAD: `22f866ab31210a0e9a741e4c17c85d363b72b288`
- branch: `roadmap/integration`
- worktree status before this handoff: clean

## Exact ancestry and ownership

The Core lane was already present at exact tip
`164d84b77e74e37d63f42dfc99ae26df1f83765c`.

Experience M00 was merged with `--no-ff` from the frozen commit
`d3730f82ea98caa1082f99d1f619cf801c7c62ff` in merge result
`9611adf1891ddfc47815f619240728bd21c2ec95`.

Verification was merged with `--no-ff` from the frozen commit
`7837d0db586f13d9cb1f104e6567cad4ce6e7f79` in the same merge result
`9611adf1891ddfc47815f619240728bd21c2ec95`. Conflict resolutions preserved
the Core integration demo and PostgreSQL gate, unified the worktree control,
and adapted the Verification execution-control assertions to the integration
lane.

The Experience tip `64a918f1f870e01d01f6dbb3229cb32086cd0f46` was explicitly
not merged. The Verification tip `07b86abcdf9fd19147e5760e2ea818e0692d8cce`
was explicitly not merged. No M04 preview paths are present in the integrated
tree. The M1 harness/evidence brought by frozen Verification is fixture-only;
it is not a Core-backed M1 capability and must not be used as one.

## Capability and acceptance

The M00 capability is the locally integrated Core baseline plus the two
consumable lane audits and verification controls. The acceptance demo was:

```text
./scripts/demo-local-integration roadmap/integration /private/tmp/umcp-roadmap-integration
```

Result: PASS. It exercised the local Core-backed write/search/update/forget
and cross-owner/auth-boundary contract selections with synthetic-only data.
The fixture cross-client demo also passed in the focused verification suite,
but remains fixture evidence only.

## Current gates and freshness

Freshness is recorded in `GATE-FRESHNESS.json`. Current passes at the tested
code HEAD:

- `gate-fast`: PASS, Ruff/mypy and 73 tests;
- PostgreSQL: PASS, PostgreSQL 16.15, pgvector 0.8.6, 19 tests,
  zero-to-head, downgrade and re-upgrade;
- SDK TypeScript: PASS;
- web test/check/build: PASS;
- conformance/verification/development focused suite: PASS, 14 tests;
- E5 semantic harness: PASS, 5 tests;
- secret/PII and synthetic runtime-output scans: PASS;
- SBOM: PASS, non-empty local CycloneDX output;
- links/claims: PASS at the pre-handoff documentation snapshot;
- `git diff --check`: PASS at the tested code HEAD.

Dependency audit is `environment-blocked`: `pip-audit` could not bootstrap
pip/wheel/setuptools in the restricted network environment. Browser E2E is
`environment-blocked`: no connected browser backend was available. Loopback
HTTP was not classified as blocked for this run because the authorized local
`gate-fast` execution passed those tests; the historical Verification-lane
loopback block remains historical evidence only.

## E5 finding M1-EVAL-001

ADR 0008 and the frozen E5 configurations use the literal prefixes
`query: ` and `passage: `, including the trailing separator space. The
minimal integration correction changed the two assertions to those literal
values. Model, revision, pooling, threshold, holdout and prefix semantics
were not changed. The affected semantic harness was rerun and passed.

The original Verification finding and artifacts remain preserved as historical
evidence; the boundary assertion mismatch is resolved in the integrated tree.

## Open findings, blockers, and prohibited claims

- Browser E2E and dependency audit remain environment-blocked.
- External IdP/KMS/HSM, production deployment, real email, durable external
  queue, holdout, real data, and independent audit are not claimed.
- Fixture-backed M1 is not integrated as product capability.
- M04 is not integrated and no M01 or M04 milestone was opened.
- This handoff does not claim production-ready status, release readiness,
  GA, universal-client support, E2EE/zero-knowledge guarantees, or an
  independent final GO.

## Next synchronization boundary

M00 is the only milestone closed in this execution. The next action, when the
roadmap is explicitly advanced, is to freeze the Core contract for the next
milestone. The parked Experience preview remains excluded until its capture
and review contract and roadmap ordering permit consumption.
