# H02 — acceptance contract (frozen)

**Status:** `frozen before implementation`
**Base SHA:** `b839ccd8ae408e0f0a095c7fdf27a165a10907d3`

## Outcome

Replace the historical unsafe GCP proposal with a local-only, reviewable IaC
and deployment-pipeline design.  The design must fail closed before any
provider action and must not require project IDs, credentials, secrets, or a
Terraform provider initialization to review its security properties.

## In scope

- Terraform declarations and variable validations for private Cloud Run,
  Cloud SQL, network, IAM, WIF, Secret Manager, KMS, state, and operations;
- a GitHub OIDC/WIF-only workflow and a deploy wrapper that refuses apply,
  unauthenticated deployment, and imperative fallback;
- a pinned-digest container contract, infrastructure runbook, and a local
  verifier that rejects the H01 prohibited patterns.

## Acceptance checks

`./scripts/validate-gcp-local` must exit zero on the delivered tree and prove
all of the following from local files:

1. no public Cloud Run invoker, `allUsers`, `--allow-unauthenticated`, static
   GCP key, `localhost` database URL, public SQL IPv4, public authorized
   network, literal runtime secret, `terraform apply`, or imperative deploy
   fallback exists in the active H02 paths;
2. the Terraform interface requires an approved CP-1/CP-3 decision record
   before any apply-capable configuration can be rendered, and defaults to a
   disabled local-review posture;
3. explicit runtime, worker, migration, deploy, and break-glass identities
   are declared with narrowly enumerated bindings; WIF trust is constrained
   to repository, ref, and environment attributes;
4. Cloud SQL is private-only behind VPC/Private Service Access and a Cloud Run
   VPC connector; runtime secret consumption uses versioned references and
   KMS permissions are narrowly scoped;
5. state is GCS-backed with locking, versioning/retention and restricted
   access intent; operations include a budget, redacted logging/monitoring
   and retention policy; and
6. workflow/container/deploy interfaces use an immutable image digest and a
   consistent `8080` port without an external action.

## Evidence boundary

The verifier is an IaC/pipeline policy test, not a Terraform plan or provider
test. Terraform `init`, `plan`, `apply`, deployment, billing, IAM, WIF, KMS,
Secret Manager, credential, network, Cloud Run, and Cloud SQL actions remain
prohibited pending CP-1 and CP-3. A passing result permits only the claim of
local fail-closed hardening; it never permits a staging or production claim.

## Rollback

Revert the H02 commits locally. No remote state, resource, credential, or
provider configuration may be created by this package.
