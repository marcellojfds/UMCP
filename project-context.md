# UMCP project context

**Updated:** 2026-08-30

## Product thesis

People build durable knowledge across ChatGPT, Claude, Gemini, coding agents,
and future assistants. That knowledge should belong to the user rather than
one model vendor. UMCP provides a neutral memory layer with explicit capture,
retrieval, provenance, correction, deletion, and portability.

## Current product

UMCP is a private staging MVP with:

- hosted MCP over Streamable HTTP;
- Google-backed OAuth and server-derived owner scope;
- PostgreSQL/pgvector persistence;
- memory write, search, capture, update, and forget;
- a browser portal for the signed-in owner's memories; and
- maintainer-account evidence across ChatGPT and Gemini Spark.

See [Current state](docs/CURRENT_STATE.md) for exact deployment evidence.

## Architectural invariants

1. Hosted clients never choose their owner or tenant.
2. Local stdio and hosted Cloud are separate trust boundaries.
3. Every memory has provenance, lifecycle state, version, and owner scope.
4. Retrieval is allowed to abstain, but direct durable facts must be reliably
   retrievable without client prompt engineering.
5. Forget is an explicit operation; exports and backups require separate
   retention/deletion handling.
6. Memory is untrusted retrieved data, never an instruction channel.
7. Logs and public evidence omit payloads, tokens, raw identity, and secrets.
8. Server-decryptable retrieval is not E2EE or zero knowledge.

## Immediate product objective

Make the already verified ChatGPT → UMCP → Gemini path feel natural:

- calibrate retrieval so plain-language queries return relevant memories;
- make capture provenance client-neutral;
- automate the cross-surface acceptance journey;
- improve login/connection guidance; and
- turn the portal from a read-only list into a user control surface.

## Deferred scope

Public marketplace publication, broad beta, billing, teams, mobile apps,
knowledge graphs, autonomous consolidation, and universal client support are
not current priorities. Claude becomes a priority only after the two verified
surfaces are reliable without workarounds.

## Documentation rule

The active sources are listed in [docs/README.md](docs/README.md). Historical
gameplans, workstreams, handoffs, and eval reports explain how the project got
here; they do not override current state or priorities.
