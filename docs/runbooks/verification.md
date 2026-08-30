# Verification runbook

## Current local gates

From a clean worktree:

```bash
./scripts/gate-fast
./scripts/gate-postgres
cd apps/web && npm test
```

Use synthetic data. A skipped required dependency or missing PostgreSQL/
pgvector environment is not a passing result.

## Documentation checks

```bash
git diff --check
./scripts/assert-doc-links-claims
```

The current status source is `docs/CURRENT_STATE.md`. Historical handoffs and
eval reports remain evidence for their own date/SHA only.

## Hosted acceptance

For an explicitly authorized staging run, record:

- exact source SHA, image digest, revision, endpoint, date, and client surface;
- OAuth discovery and callback result without codes/tokens;
- tool list and scoped lifecycle result without memory payloads;
- owner-isolation, refresh, expiry, revocation, and destructive-action result;
- portal visibility for the same owner; and
- cross-surface recall with a synthetic memory.

The current P0 acceptance must prove a plain-language ChatGPT write followed by
a plain-language Gemini Spark recall **without** setting `min_relevance`.

## Historical verification tooling

Scripts and reports under `docs/handoffs/roadmap/` capture earlier milestones.
They are useful regression inputs but their old branch/worktree instructions
must not be resumed as current operations.
