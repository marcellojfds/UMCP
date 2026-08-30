# GCP hosted architecture — H01 historical design contract

**Status:** `historical-baseline / superseded-by-private-staging-evidence`

This contract records the pre-deployment architecture baseline that guided
H02--H06. It must not be read as current remote-state evidence. The private
staging implementation and its remaining gaps are documented in
[`../CURRENT_STATE.md`](../CURRENT_STATE.md), the runbooks, and the current
threat model.

## Target topology and controls

| Boundary | Frozen local design | Required proof before hosted claim |
| --- | --- | --- |
| Edge and MCP | An approved HTTPS edge forwards only to private Cloud Run ingress. `/mcp` is Streamable HTTP with no HTTP downgrade; `/healthz` and `/readyz` are separate, redacted routes. No unauthenticated public Cloud Run invoker. | H03 local black-box conformance, then H07 authorized HTTPS/MCP evidence. |
| Identity | Gateway verifies OIDC/OAuth authorization-code-with-PKCE tokens and server-side consent/revocation before constructing `Principal`. Request `owner_id`/`tenant_id` is rejected. IdP/email remains unselected. | CP-2 plus H04 negative and integration tests. |
| Deploy trust | GitHub Actions authenticates through GitHub OIDC to a narrowly bound Workload Identity Federation provider and a dedicated deploy service account. No JSON service-account key. | CP-3 plus H02 reviewed, redacted plan and later identity audit. |
| Runtime trust | Dedicated runtime service account receives only Cloud SQL client, named-secret accessor, required KMS crypto operation, logging/metrics write, and queue permissions needed by its component. It cannot deploy, migrate, impersonate broad accounts, or manage keys. | CP-3 plus H02 IAM review and H07 effective-principal evidence. |
| Data plane | Cloud SQL PostgreSQL/pgvector has private IP only, dedicated VPC plus Private Service Access, and an approved Cloud Run-to-SQL private connector/integration. Public IPv4 and public authorized networks are forbidden. | CP-1/CP-3 plus H02 plan, H06 RLS/migration tests and H07 connectivity proof. |
| Database roles | Restricted runtime role, migration role, and time-bounded audited break-glass role are distinct. All tenant tables use `tenant_id`, FORCE RLS, default deny, composite tenant constraints and transaction-local context from verified `Principal`. | H06 adversarial tests and authorized staging audit. |
| Secrets and crypto | Secret Manager supplies versioned runtime references; Terraform never interpolates a secret value into a runtime env var. GCP KMS holds KEKs used by the application envelope adapter; KMS failure is fail-closed. | CP-3 plus H02 secret/IAM review, H06 KMS/swap/restore tests. |
| Operations | Redacted structured logs/metrics/traces, budget alerts, quota/rate limits, deployment audit, image digest policy, and backup inventory are required before hosted data. Backups restore only into isolation and replay tombstones before traffic. | H02 local configuration review; H06 restore tests; H07 operational evidence. |

## Component ownership matrix

| Principal | Intended responsibility | Explicit exclusions |
| --- | --- | --- |
| GitHub WIF deploy SA | approved artifact deployment to the staging runtime | runtime data, KMS decrypt, secret reading, migration, broad IAM |
| migration SA / DB migration role | additive, reviewed schema/data migration | serving traffic, OAuth, general deploy, break-glass |
| runtime API SA | serve verified MCP/API requests and retrieve only named runtime dependencies | Terraform, deploy, user/role management, arbitrary secret/key access |
| worker SA | tenant-bound signed jobs and their named dependencies | request authentication, migration, deploy, broad data access |
| break-glass | time-bound, justified recovery with redacted audit | normal serving, standing access, hidden bypass of RLS/audit |

Exact account IDs, project IDs, IAM bindings, key IDs, secret names, database
instance names, budget amount, alert destinations, and domains are deliberately
unassigned. Assigning them is an external control-plane decision at CP-1 or
CP-3, not a documentation default.

## Required local replacements

H02 must remove or reject these observed-proposal patterns before any apply:

- `allUsers` invoker or `--allow-unauthenticated`;
- `GCP_SA_KEY` or any static CI credential;
- Cloud SQL public IPv4, public authorized network, or database at
  `localhost` without an approved private connection mechanism;
- password or token interpolation into Terraform/runtime environment;
- a KMS key or Secret Manager secret not consumed through the stated boundary;
- `terraform apply -auto-approve` and imperative deploy fallback.

## Checkpoint release criteria

CP-1, CP-2, and CP-3 are approvals to begin narrowly scoped external work,
not hosted acceptance. The exact decision record must identify owner, scope,
expiry/review date, rollback authority, cost limit where applicable, and no-go
conditions. A missing record blocks the relevant external action while leaving
local implementation and documentation possible.

## Claims boundary

This historical document alone permits no runtime claim. Current claims about
private staging require the evidence indexed by `docs/CURRENT_STATE.md`.
Production, E2EE/zero-knowledge, verified backup/restore, and regional-residency
claims remain prohibited without new evidence.
