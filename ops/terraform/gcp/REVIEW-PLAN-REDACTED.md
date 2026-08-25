# H02 redacted local resource projection

**Status:** `local static review; not a Terraform provider plan`

This projection is derived from the checked-in configuration without backend
initialization, provider plugins, credentials, or a provider request. It
contains no project ID, billing account, image repository, secret payload,
database URL, key material, account email, state bucket target, or decision
record value.

## Expected additive objects after future CP-1/CP-3 authorization

| Area | Declared objects | Local safety assertion |
| --- | --- | --- |
| Checkpoints | one Terraform guard | defaults block all external changes |
| Identity | five dedicated service accounts, narrow project bindings, one GitHub OIDC WIF pool/provider | no default service account, static key, broad impersonation, or public principal |
| Network | one custom VPC, PSA range/connection, one Serverless VPC connector | no public database path |
| Data | one PostgreSQL instance and application database | private IP only, encrypted-only transport, backups/PITR, deletion protection |
| Secrets/KMS | one regional versioned secret reference, one key ring/key, named accessor/crypto bindings | no secret payload or mutable version in configuration |
| Runtime | one internal-load-balancer-only Cloud Run service | explicit runtime service account, all private connector egress, digest-only image, port 8080, no invoker binding |
| Operations | one versioned/retained private state bucket, budget, logging sink and alert policy | no public state bucket or runtime state access |

## No destructive operations accepted

The source sets database deletion protection and KMS lifecycle protection. Any
future provider review that contains a delete, replace, public IAM binding,
public SQL address, mutable secret reference, unpinned image, or a resource
outside this table is a no-go until independently reviewed. This document is
not evidence of resource creation, a provider plan, staging, or production.
