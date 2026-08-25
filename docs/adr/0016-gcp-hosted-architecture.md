# ADR 0016 — GCP-targeted hosted architecture and evidence boundary

## Status

Accepted as a **local architecture decision** for H01 (2026-08-25). It
supersedes the historical AWS recommendation in
`M02-PROVIDER-DECISION.md`; it does not authorize, attest, or recreate any
GCP resource.

## Context

`M02-PROVIDER-DECISION.md` recommended AWS `sa-east-1` before the repository
recorded a GCP adoption attempt. The canonical inventory and the GCP adoption
gap report subsequently found GCP Docker, Terraform, workflow, runtime, and
handoff artifacts, but classify them only as a local proposal and `PARTIAL /
NOT-READY`. A reported Cloud Run health response, Terraform source, a billing
record, or a historical deployment handoff does not prove the hosted controls
required by ADRs 0010--0013.

The divergence must be resolved without re-running provider checks or treating
the observed artifacts as authorization.

## Decision

1. GCP is the conditional target for the first hosted staging architecture,
   replacing AWS as the repository's forward design target. The intended
   regional placement for GCP workload, database, keys, secrets, and primary
   logs is `southamerica-east1`.
2. This is not an authorization to use an existing project, link billing,
   enable APIs, create a resource, register an IdP client, create a secret or
   key, change IAM, deploy, run Terraform, or accept hosted traffic. The
   existing GCP state remains `PARTIAL / NOT-READY` until independently
   verified after the appropriate checkpoints.
3. The residency statement is deliberately limited: the architecture intends
   to locate the listed primary data-plane services in `southamerica-east1`.
   It does not promise Brazilian residency for identity metadata, email,
   support, telemetry exports, artifact distribution, backup/DR copies, or
   any managed-provider control plane. Cross-region replication is prohibited
   by this architecture until separately approved.
4. H02 must replace—not apply—the unsafe local GCP proposal: public invoker,
   static CI key, public Cloud SQL IPv4, `localhost` database URL, direct
   password interpolation, unused Secret Manager/KMS, and imperative
   unauthenticated deploy fallback are rejected design inputs.
5. The IdP/email product is intentionally **not selected**. H01 freezes the
   required interface and two-candidate, authorized spike; CP-2 is the human
   decision point. Likewise, exact project, budget, domain, owners, service
   accounts, KMS key ownership, and break-glass policy are not inferred.

## Architecture boundaries

The authoritative H01 design contract is
[`gcp-hosted-architecture-h01.md`](../contracts/gcp-hosted-architecture-h01.md).
It preserves these non-negotiable boundaries:

- Internet/client -> HTTPS edge -> verified immutable `Principal` -> shared
  application façade -> transaction-scoped PostgreSQL/RLS.
- Worker jobs cross a signed, tenant-bound envelope boundary; neither a
  request nor a queue payload authorizes an arbitrary tenant.
- Runtime KMS/Secret Manager access is separate from deploy, migration, and
  break-glass access; no secret value belongs in Git, Terraform values, plans,
  logs, or runtime literal environment variables.
- `/mcp` is the exact future Streamable HTTP endpoint; health/readiness are
  separate, non-sensitive routes and never substitute for MCP/auth readiness.

## Dependencies and checkpoints

| Checkpoint | Human decision required before action | Action still prohibited before approval |
| --- | --- | --- |
| CP-1 | exact GCP project/environment, `southamerica-east1`, named owner, monthly budget/alerts, domain/edge boundary, and blast radius | API enablement, billing, Terraform apply, networking, Cloud Run/SQL creation, deploy |
| CP-2 | IdP/email provider selected from an authorized comparison of at most two candidates; redirect URIs, client type, scopes, email behavior, privacy/cost owner | IdP account/client registration, redirect activation, email sending, OAuth test flow |
| CP-3 | named owners for runtime/migration/deploy/break-glass, KMS/secret ownership, rotation, revocation, audit retention and break-glass TTL | service accounts, IAM grants, WIF trust, keys, secrets, credentials, KMS/Secret Manager use |

H02 consumes the landing-zone and IaC interfaces; H03 the edge/MCP interface;
H04 the IdP and principal interface; H06 the database, KMS, secret, worker and
restore interfaces. H07 alone may assess a staging integration after CP-1,
CP-2, and CP-3 are approved and its own evidence is current.

## Exit and rollback

The portability exit is PostgreSQL schema/migrations plus authorized,
content-safe export procedures and provider-neutral application contracts; it
does not depend on a GCP proprietary tenant/RLS semantic. Before any remote
action, rollback means no-go and retaining local documentation. After a future
approved deployment, it means disable ingress, revoke affected clients and
credentials, stop workers, preserve redacted audit evidence, and use only a
tested isolated restore with tombstone replay. It never means a destructive
migration downgrade or deletion of audit evidence.

## Consequences

No current evidence supports claims of deployed GCP, private network, WIF,
OAuth/OIDC, RLS, KMS integration, restore, data residency, staging readiness,
beta, production, or release. Those claims remain prohibited until the named
downstream gates pass on an authorized target.
