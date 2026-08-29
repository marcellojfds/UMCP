# Roadmap

The roadmap separates the private managed MVP path from later open-source and
public-release work. Current operational status is tracked in
[`roadmap_implementation.md`](roadmap_implementation.md) and the current resume
handoff is
[`MVP-RESUMPTION-20260829.md`](handoffs/roadmap/MVP-RESUMPTION-20260829.md).

## Current position — 2026-08-29

- M2 is staging-ready on `umcp-cloud-staging-00018-f78`; this is not a
  production or public-beta claim.
- C01/C02 implementation exists and produced 14/14 plus 15/15 hosted results,
  with containment at 0/0/0. Their gates remain open pending one clean rerun
  from an audit image tied to the exact committed source SHA.
- C03 is the next product step: one authorized external client surface under
  CP-4. No landing page, dashboard or third-party invitation is ready yet.
- The first go-to-market step is a private managed beta. Open-source release
  remains after the operated private beta, as defined by blocks B and O.

## Productization program

The long-term portable-memory product direction and its Codex delivery sequence
are maintained separately so they do not imply that Alpha capabilities are
already released:

- [Portable Memory product vision](PRODUCT_VISION_PORTABLE_MEMORY.md)
- [Codex delivery roadmap](CODEX_DELIVERY_ROADMAP.md)
- [Terra/Luna productization gameplan](GAMEPLAN_PRODUCTIZATION_TERRA_LUNA.md)
- [Codex execution reliability playbook](EXECUTION_RELIABILITY_PLAYBOOK.md)

## Historical Alpha release-candidate track

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

## Hosted capabilities that were future work at Alpha

- a trusted identity/authentication boundary and hosted tenant isolation;
- client-side encryption or another reviewed cryptographic design;
- embedding providers, reranking, consolidation, and other quality work with
  new evals and budgets;
- transports and SDKs beyond Python/MCP stdio;
- scale/load claims backed by measurements.
