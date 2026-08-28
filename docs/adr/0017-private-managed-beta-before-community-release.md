# ADR 0017 — Private managed beta precedes Community release

## Status

Accepted (2026-08-28).

## Context

UMCP needs evidence from a small, consented group before committing to a
public, self-hosted distribution surface. Community packaging, multi-platform
installation, public SDK support, release signing, governance, and public
compatibility claims are valuable work, but do not make OAuth, tenant
isolation, revocation, recovery, or beta operations safer.

## Decision

UMCP will first operate as a **private managed beta**. Until the M6 gate is
closed, the repository, hosted service, connectors, SDKs, and operational
documentation remain private and are available only to project operators and
explicitly consented invitees.

M7 remains a required roadmap milestone, but it is sequenced **after** the
private beta is operated and audited (B04T). It is not a prerequisite for M6.
M8 public beta/GA continues to require both the private-beta evidence and the
independent M7 release audit.

This decision does not relax any identity, PKCE, revocation, RLS, KMS,
backup/restore, logging-redaction, rate-limit, incident, consent, quota, or
rollback gate. A managed beta is not production-ready, public beta, or GA.

## Consequences

- The critical path is M2 → M3 → M4 → M5 → M6, with no public source or
  self-hosting claim before M7.
- B04 requires explicit CP-6 approval, a 5–20-person consented cohort, low
  quotas, a kill switch, rollback, and active incident/security reporting.
- Public artifacts, tags, releases, documentation promises, and Community
  installation support remain prohibited until M7 is independently audited.
- ADR 0009 still defines the two eventual compositions; this ADR changes only
  release sequence and availability.
