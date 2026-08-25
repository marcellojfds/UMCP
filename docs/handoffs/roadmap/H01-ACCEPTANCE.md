# H01 — acceptance contract (frozen)

**Status:** `frozen before implementation`
**Base SHA:** `74c044cbecdd2a95716e674876e7041aac3f9cd4`

## Outcome

Reconcile the historical AWS recommendation with the repository's later GCP
adoption record, and freeze a GCP-targeted hosted architecture as a local
design only. The result must distinguish an adopted architectural target from
remote state: the GCP artifacts remain `PARTIAL / NOT-READY`, and no hosted,
staging, deploy, billing, or production claim is accepted.

## Acceptance checks

The H01 documentation is acceptable only when one clean local candidate
contains all of the following:

1. an ADR that explicitly supersedes the historical AWS recommendation,
   selects GCP `southamerica-east1` as a conditional target, limits the
   data-residency claim, and records a PostgreSQL export/teardown exit path;
2. a hosted architecture that assigns boundaries, service-account roles, IAM
   least-privilege intent, GitHub WIF, private database connectivity, secrets,
   KMS ownership, logging, rollback, and the H02--H06 handoff interfaces;
3. the GCP gap report's P0 findings remain open rather than being overwritten
   by Terraform, workflow, healthcheck, or historical-handoff assertions;
4. CP-1, CP-2, and CP-3 each name the exact human decision required before
   any corresponding external action; and
5. no provider command, Terraform action, deployment, network/IAM/KMS/secret
   mutation, credential handling, paid service, or external lookup is run.

## Local verification commands

```text
git diff --check
rg -n 'AWS|GCP|southamerica-east1|PARTIAL / NOT-READY|CP-1|CP-2|CP-3' \
  docs/adr/0016-gcp-hosted-architecture.md \
  docs/contracts/gcp-hosted-architecture-h01.md \
  docs/threat-model-hosted-h01-delta.md \
  docs/handoffs/roadmap/M02-GCP-ADOPTION-GAP-REPORT.md
git diff --name-only 74c044cbecdd2a95716e674876e7041aac3f9cd4..HEAD
```

These checks verify documentary consistency only. They do not verify a cloud
provider, OAuth/OIDC, IAM, WIF, networking, Cloud SQL, Secret Manager, KMS,
backup/restore, hosted MCP, or any remote endpoint.

## Gate rule and rollback

H01 may be marked complete only if the architecture documents the required
human checkpoints without inventing their approvals, and all local acceptance
checks pass. If a required decision is absent, the work remains documented but
H01 remains unchecked; it does not open H02--H07.

Rollback is a local revert of the H01 documentation commits. No remote state
may be created or changed by this package.
