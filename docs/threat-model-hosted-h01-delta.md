# Threat-model delta — H01 GCP-targeted architecture (historical)

**Status:** `historical-design-delta / superseded-by-staging-evidence`

This delta supplements `threat-model-hosted-v1.md`. It does not reduce any
existing no-go condition. It records the risks considered before deployment;
use [`CURRENT_STATE.md`](CURRENT_STATE.md) and
[`threat-model-hosted-v1.md`](threat-model-hosted-v1.md) for the current private
staging boundary.

| GCP-specific threat | Required architectural control | Evidence required later | No-go condition |
| --- | --- | --- | --- |
| public Cloud Run bypasses the gateway | no `allUsers`; ingress reachable only through approved HTTPS edge | H02 reviewed plan; H07 external authorization test | unauthenticated route reaches MCP/runtime |
| static CI credential exfiltration | GitHub OIDC WIF, repository/branch/environment-bound trust and deploy-only SA | H02 policy review and H07 audit | JSON key or overbroad deploy identity |
| public SQL or accidental default SA | private IP/VPC/PSA/connector, explicit runtime SA and restricted DB role | H02 design; H06/H07 connection and role evidence | public DB path, default SA, unscoped DB role |
| secret or KMS misuse | versioned secret references, named accessor bindings, KMS KEK/decrypt boundary, redacted logs | H02 review; H06 failure/rotation/restore tests | literal secret/state leak, plaintext fallback, unlogged broad key access |
| IdP or email data leaves intended boundary | CP-2 provider decision documents data flows, redirects, scopes, cost and retention | authorized two-candidate spike and H04 tests | implied residency, unapproved client/email flow |
| restore resurrects deletes | encrypted backup inventory, isolated restore, tombstone replay before traffic | H06/H07 restore exercise | traffic before tombstone/revision/RLS/key validation |
| cost or control-plane abuse | CP-1 budget/owner/blast radius and CP-3 audit/rotation/break-glass decisions | approved budget signals and H07 exercise | paid resource or IAM/KMS action without checkpoint |

The residual v1 risk remains server-decryptable operator access. This delta by
itself proves no deployed control. It does not support E2EE, zero-knowledge,
universal-encryption, residency, or production claims.
