# H01 — GCP decision reconciliation and hosted architecture handoff

**Status:** `DONE / local-documentary-architecture-only`
**Base SHA:** `74c044cbecdd2a95716e674876e7041aac3f9cd4`
**Acceptance freeze SHA:** `7183a8c9dba28be37128d95e3de17876654ac20d`
**Architecture delivery SHA:** `cf1fdc0d6141332d548b2ac57e826387c44d65e1`

## Acceptance and outcome

`H01-ACCEPTANCE.md` was committed before the architecture implementation. H01
is complete as a local decision/contract gate: ADR 0016 formally supersedes
the historical AWS recommendation with GCP `southamerica-east1` as the
conditional hosted target; the H01 contract defines interfaces and controls
for H02--H06; and the threat-model delta preserves the GCP-specific no-go
conditions.

The decision does **not** promote the GCP proposal. The authoritative status
of the observed GCP artifacts remains `PARTIAL / NOT-READY`; no remote health,
Terraform, workflow, billing record, or historical handoff was treated as
proof of a deployed or secure hosted service.

## Changed paths

- `docs/handoffs/roadmap/H01-ACCEPTANCE.md`
- `docs/adr/0016-gcp-hosted-architecture.md`
- `docs/contracts/gcp-hosted-architecture-h01.md`
- `docs/threat-model-hosted-h01-delta.md`
- `docs/roadmap_implementation.md` — only H01 changed from `[ ]` to `[x]`
- `docs/handoffs/roadmap/H01-DONE.md`

## Current local checks

| Gate | Freshness | Result |
| --- | --- | --- |
| `git diff --check 74c044c..HEAD` | current | PASS |
| required H01 files exist (`test -f`) | current | PASS |
| architecture evidence scan for supersession, `PARTIAL / NOT-READY`, CP-1/2/3 and external-action boundary | current | PASS |
| `git diff --name-only 74c044c..HEAD` path audit | current | PASS — only the six H01 documentation/checklist paths above at handoff preparation |
| unit/contract/application suites | not-run | not needed for a documentation-only change; no source, IaC, workflow, dependency, or test path changed |

## Decisions, controls, and external checkpoints

- GCP is the conditional forward design target; the old AWS recommendation is
  historical and superseded, not silently erased.
- Primary workload/data-plane intent is `southamerica-east1`; no absolute
  residency claim is made for identity, email, control plane, telemetry,
  artifacts, backup/DR, or support flows.
- The frozen design requires private Cloud SQL/VPC/PSA/connector, explicit
  least-privilege runtime/migration/deploy/worker/break-glass identities,
  GitHub OIDC WIF instead of a static CI key, Secret Manager references, KMS
  fail-closed envelope integration, FORCE RLS, signed jobs, redacted signals,
  and isolated restore with tombstone replay.
- CP-1 precedes project/budget/region/edge and all provider/apply/deploy work;
  CP-2 precedes IdP/client/email/redirect decisions; CP-3 precedes IAM/WIF,
  KMS, secrets, credentials, rotations, and break-glass configuration.

## Skips and claim boundary

No provider command, Terraform init/plan/apply, deployment, Cloud Run/SQL,
network, IAM, KMS, Secret Manager, credential, billing, paid service, external
lookup, DNS, OAuth client, staging promotion, release, or production action
was run. No source code or GCP/IaC/workflow/deploy script was changed.

Permitted claim: a local/documentary GCP-targeted architecture and the
downstream interface/checkpoint contract are frozen. Prohibited claims: GCP
resource existence or readiness; private networking; WIF/IAM effectiveness;
OAuth/OIDC; Secret Manager/KMS integration; RLS; backup/restore; hosted MCP;
staging; beta; production; release; or absolute data residency.

## Rollback and next blockers

Rollback is a local revert of the H01 commits; no remote state exists from
this package. H02 is the next implementation package but cannot apply or
deploy until CP-1 and CP-3 decisions are explicitly recorded. H03/H04/H06
also consume this contract; H04 remains blocked on CP-2's authorized
two-candidate IdP/email decision. H07 remains blocked on all three checkpoints
and current evidence for its own staging gate.
