# H02 GCP infrastructure review runbook

**Status:** `local-review-only / provider actions blocked`

## Purpose

This runbook reviews the H02 Terraform and pipeline boundary without contacting
GCP. It does not establish a project, billing account, identity, network,
secret, KMS key, state bucket, Cloud Run service, Cloud SQL instance, staging,
or production environment.

## Local review

Run from a clean H02 worktree:

```text
./scripts/validate-gcp-local
terraform fmt -check -recursive ops/terraform/gcp
git diff --check
```

The first command is the acceptance gate. It rejects unsafe public access,
static keys, public SQL, local database endpoints, mutable/literal runtime
secrets, imperative provider commands, and missing controls. `terraform fmt`
is formatting-only. `validate` requires initialized provider plugins and is
therefore intentionally not run in this local package; the structural verifier
checks all H02 security invariants without provider initialization.

## External-action boundary

Do not initialize a backend, render a provider plan, mutate a provider, or
deploy from H02. The local `scripts/deploy-gcp.sh` always exits 78.

Before a separately approved operator introduces an external review or
promotion procedure, the decision record must contain both CP-1 and CP-3:

- CP-1: named project/environment owner, cost ceiling and alerts, region,
  edge/domain boundary, blast radius, expiry, rollback authority and no-go;
- CP-3: named runtime/migration/deploy/break-glass owners, WIF scope, KMS and
  Secret Manager ownership, rotation/revocation, audit retention, TTL,
  rollback authority and no-go.

The operator must keep the decision record out of Terraform variables except
for its non-secret identifier. H02 defaults (`cp1_approved=false` and
`cp3_approved=false`) force the infrastructure guard to fail.

## State and rollback intent

The future backend is a GCS state bucket configured for uniform bucket access,
public-access prevention, versioning and retention. GCS state locking is used
through the `gcs` backend; no backend target is committed. The deploy identity
is the only declared state writer; runtime, worker, migration and break-glass
identities receive no state access.

Rollback for H02 is a local Git revert. For any future authorized environment,
rollback must be approved independently, prefer an ingress stop or a
previously reviewed immutable revision, and never use a destructive database
downgrade. H02 makes no staging or production claim.
