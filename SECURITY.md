# Security policy

## Status and scope

UMCP is a private staging MVP and local/self-hosted engineering project. This
policy covers implementation vulnerabilities in this repository and the
maintainer-operated staging service. It does not promise production readiness,
an SLA, E2EE, zero knowledge, or protection from an authorized operator.

## Reporting a vulnerability

Use GitHub Private Vulnerability Reporting in the repository Security tab. Do
not open a public issue containing exploit details, credentials, tokens,
memory content, embeddings, database URLs, exports, or personal data.

If private reporting is unavailable, contact the maintainer through a private
GitHub channel and identify the message as security-sensitive. No separate
security email or response-time SLA is currently published.

Include:

- affected commit, deployment mode, and client surface;
- a synthetic-data reproduction;
- impact and likely boundary crossed;
- redacted logs or request identifiers; and
- a suggested mitigation if available.

## Security boundaries

- Hosted MCP verifies UMCP tokens and derives owner/tenant server-side.
- Local stdio trusts caller-provided `owner_id` and is not a remote
  authorization boundary.
- Memory content, provenance, vectors, OAuth/session data, exports, and
  backups are sensitive.
- The hosted server decrypts memory for retrieval; privileged operator access
  remains a modeled risk.
- A cross-owner read/write, raw token or memory payload in logs, OAuth bypass,
  RLS bypass, plaintext fallback after KMS failure, or resurrection after
  forget/restore is a release-blocking issue.

See [Privacy](docs/privacy.md), the [hosted threat model](docs/threat-model-hosted-v1.md),
and [Known issues](docs/known-issues.md).
