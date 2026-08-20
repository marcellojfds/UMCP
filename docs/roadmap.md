# Roadmap

The roadmap separates work that is required to audit this release candidate
from capabilities that are intentionally future work.

## Release-candidate completion

- **Committed:** keep the public docs, protocol schemas, privacy claims, and
  support matrix aligned with executable behavior.
- **Required before publication:** obtain the missing S04 retrieval report and
  S05 privacy/operations handoff; run the S07 build, clean-room, link, secret,
  and package audit; enable/verify private vulnerability reporting.
- **Planned publication:** GitHub Release only. PyPI is not part of this plan.

## Alpha follow-ups

- reproducible dependency constraints and release provenance;
- verified backup, restore, forget, retention, outage, and incident runbooks;
- an explicit maintainer decision on `hash/v1` after the frozen eval report;
- additional regression coverage for privacy and cross-owner behavior.

## Future, not promised by Alpha

- a trusted identity/authentication boundary and hosted tenant isolation;
- client-side encryption or another reviewed cryptographic design;
- embedding providers, reranking, consolidation, and other quality work with
  new evals and budgets;
- transports and SDKs beyond Python/MCP stdio;
- scale/load claims backed by measurements.
