# Verification lane runbook

Run every phase from `/private/tmp/umcp-roadmap-verification` on
`roadmap/luna-verification`.

## Preflight

```sh
scripts/assert-worktree-context --require-clean
scripts/capability-preflight --json docs/handoffs/roadmap/capability-preflight.json
```

The capability report distinguishes missing tools and daemon/browser limits
from product failures. A browser gate is never marked pass from a static render
or a local-file navigation attempt.

## Independent demos

```sh
scripts/demo-local-integration
scripts/demo-cross-client-memory
scripts/demo-memory-inbox
scripts/demo-concepts-and-notes
scripts/demo-backup-delete-restore
```

All five demos use disposable synthetic state, print identifiers/status only,
and return non-zero on assertion failure. The fixture is a harness test, not
evidence that Core has implemented the behavior.

## Gate freshness

```sh
scripts/check-gate-freshness docs/handoffs/roadmap/GATE-FRESHNESS.json --markdown
```

Use only `current`, `historical`, `not-run`, or `environment-blocked`. Every
row needs the SHA that was actually tested and a reason when it was not run or
was blocked.

## Stagnation

```sh
scripts/detect-stagnation path/to/event-log.json
```

Exit 1 is an intervention signal, not a product failure: stop adding features,
reduce to a minimal reproducer, checkpoint, try a safe alternative and update
the milestone contract.

## Ownership and claims

Do not edit `src/omp`, migrations, `apps/web`, SDK implementation, auth/crypto/RLS
or product copy. Findings go to
`docs/handoffs/roadmap/findings/<milestone>-<id>.md`. No holdout, push, PR,
deploy, real data, compromised secret, paid service or independent GO.
