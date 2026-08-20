# Security policy

## Status

Open Memory Protocol is an alpha, local/self-hosted project. This policy is
for reporting implementation vulnerabilities; it is not a promise of hosted
security, tenant isolation, E2EE, zero knowledge, or privacy from an operator.

## Reporting a vulnerability

Use GitHub Private Vulnerability Reporting in the repository Security tab. Do
not put secrets, memory contents, embeddings, exports, or exploit details in a
public issue or pull request. This local S06 session did not change GitHub
repository settings, so the maintainer must enable and verify the private
reporting channel before publication.

There is no separate security email published at this time. If private
reporting is unavailable, do not disclose sensitive details publicly; contact
the repository maintainers through a private GitHub channel and state that the
report is security-sensitive.

Please include the affected version/commit, deployment mode, reproduction
steps using synthetic data, impact, and any suggested mitigation. Redact real
memory content and credentials.

## Scope and response

Supported scope is the code and release artifacts in this repository. The
supported runtime is local/self-hosted with PostgreSQL 16 + pgvector and MCP
stdio. A deployment that exposes `owner_id` to untrusted users is outside the
Alpha security boundary: in local stdio composition `owner_id` is client-
provided and trusted, not an authentication credential.

The maintainers will acknowledge reports when practical, assess severity, and
coordinate a fix or advisory. No response-time SLA is promised for this alpha.

## Sensitive data model

Memory content, provenance/evidence, relations, exports, backups, and
`hash/v1` embeddings are sensitive. Embeddings are not anonymous. The default
export omits vectors, but exports remain sensitive and can be copied outside
the database. See [`docs/privacy.md`](docs/privacy.md) and
[`docs/threat-model.md`](docs/threat-model.md).
