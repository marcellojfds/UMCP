# GCP staging operations

**Status:** private staging exists; checked-in deployment automation remains
fail-closed.
**Environment:** `umcp-mcp-staging-20260825`, `us-central1`.

## Current deployment identity

The canonical current values live in [Current state](../CURRENT_STATE.md).
Before any investigation, compare Cloud Run's active revision, image digest,
and `source_sha` label with that file. Do not infer the current service from an
older H07/T02 handoff.

## Safe read-only checks

```bash
gcloud run services describe umcp-cloud-staging \
  --project umcp-mcp-staging-20260825 \
  --region us-central1

gcloud logging read \
  'resource.type="cloud_run_revision" AND resource.labels.service_name="umcp-cloud-staging"' \
  --project umcp-mcp-staging-20260825 --limit=100
```

Never print secret values, database URLs, bearer tokens, cookies, OAuth codes,
memory bodies, or raw email addresses. Prefer status codes, tool names,
redacted request IDs, revision names, digests, and counts.

## Promotion boundary

`scripts/deploy-gcp.sh` intentionally exits without contacting GCP. Current
staging promotions were operator-controlled, not a reusable production
pipeline. A future promotion must:

1. start from a clean committed SHA;
2. build an immutable digest tied to that SHA;
3. deploy a no-traffic revision;
4. apply/verify migrations with the same image provenance;
5. run OAuth, MCP, owner isolation, portal, and cross-client canaries;
6. move traffic only after all gates pass; and
7. preserve a known-good rollback revision.

Database rollback uses forward fixes or a verified restore, never destructive
schema downgrade against shared data.

## Production prohibition

This runbook does not authorize a production project, public beta, DNS/domain
change, new user enrollment, billing expansion, IAM broadening, secret access,
or destructive operation.
