# H02 — local GCP IaC and pipeline hardening handoff

**Status:** `DONE / local fail-closed hardening only`
**Canonical base SHA:** `b839ccd8ae408e0f0a095c7fdf27a165a10907d3`
**Acceptance freeze SHA:** `8636bca`
**Implementation SHA:** `77fec9dc4550a40d13ae61027b59a869359ac367`
**Branch:** `codex/h02-gcp-hardening`

## Outcome

H02 replaces the historical unsafe proposal with local, reviewable Terraform
and a review-only workflow. The implementation has no configured provider
target, no credential, no secret payload, and no deployment path. Its local
policy gate fails closed on the rejected H01 patterns and the deploy wrapper
always returns exit 78.

## Changed paths

- `ops/terraform/gcp/` — private network/PSA/connector and Cloud SQL, explicit
  identities/IAM/WIF, KMS/secrets, private Cloud Run, state/operations,
  checkpoint guard, and a redacted static resource projection;
- `.github/workflows/gcp-review.yml` — offline policy and format review only;
- `Dockerfile` — non-root container, immutable-base syntax and port `8080`;
- `scripts/validate-gcp-local` and `scripts/deploy-gcp.sh` — local policy gate
  and an intentionally blocked deploy entrypoint;
- `docs/runbooks/gcp-infrastructure.md` and
  `docs/handoffs/roadmap/H02-ACCEPTANCE.md` — operating boundary and frozen
  acceptance contract;
- `docs/roadmap_implementation.md` — only the H02 checkbox changed.

## Current local evidence

| Gate | Freshness | Result |
| --- | --- | --- |
| `./scripts/validate-gcp-local` | current | PASS — rejects public invoker/static key/public SQL/local DB/secret mutation/provider mutation patterns and requires private networking, explicit identities, constrained WIF, versioned secret ref, KMS, state, budget/logging/alert and digest controls. |
| direct policy-rule negative (`allUsers`) | current | PASS — exits non-zero for a synthetic public-invoker token. |
| `python3 -m py_compile scripts/validate-gcp-local` | current | PASS |
| Ruby YAML parse of `.github/workflows/gcp-review.yml` | current | PASS |
| local HCL whitespace/brace structural check | current | PASS |
| `./scripts/deploy-gcp.sh` | current | PASS — exits `78`, with no provider command. |
| `git diff --check` | current | PASS |
| redacted review projection | current | PASS — additive objects only; delete/replace/public/mutable/unpinned drift is a no-go. |
| `terraform fmt -check -recursive ops/terraform/gcp` | not-run | Terraform binary is absent in this worktree; the CI review workflow retains this offline formatting command. |
| `terraform validate` | not-run | intentionally not attempted: no initialized provider plugins/backend and H02 prohibits provider initialization; the local structural policy gate substitutes only for the security-boundary review, not provider validation. |
| provider plan/apply/deploy/remote tests | not-run | prohibited by the package boundary. |

## Controls now represented locally

- no Cloud Run invoker IAM binding; ingress is internal-load-balancer-only;
- separate runtime, worker, migration, deploy and break-glass identities;
  deploy receives only Cloud Run developer, Artifact Registry writer, WIF user
  and state-writer intent; runtime/worker are limited to their named SQL,
  secret and KMS operations;
- GitHub OIDC WIF condition binds repository, protected ref and environment;
  no static CI key path exists;
- Cloud SQL has private IP only, no authorized network, VPC/PSA and a Serverless
  VPC connector; deletion protection, backup and PITR are declared;
- database URL is a versioned Secret Manager reference, never an inline value;
  KMS permissions are scoped to the named envelope key;
- the future GCS state design has public-access prevention, uniform access,
  versioning, retention and GCS locking; its target remains unset;
- image input requires a SHA-256 digest, container and Cloud Run use `8080`,
  and budget/logging retention/monitoring are declared.

## Skips and claims boundary

No Terraform initialization, provider plan, provider mutation, deployment,
billing, IAM, WIF, KMS, Secret Manager, credential, network, Cloud Run, Cloud
SQL, external lookup, staging, production, release or paid-service action was
run. The allowed claim is local fail-closed hardening of an unconfigured GCP
design. It is not evidence that any listed GCP control exists or works, nor a
staging/production/region/residency claim.

## Rollback and next blockers

Rollback is a local revert of `8636bca`, `77fec9d`, and this closing handoff
commit. No remote state was produced. CP-1 must name the project/environment,
owner, budget, edge and blast radius; CP-3 must name IAM/WIF/KMS/secrets
owners, audit/rotation/revocation and break-glass policy before any provider
or credential action. H03/H04/H06 still own hosted MCP, identity, RLS/KMS
runtime integration and recovery proof; H07 alone may assess staging after all
required checkpoints and current external evidence.
