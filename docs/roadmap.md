# UMCP roadmap

**Updated:** 2026-08-30
**Current stage:** private staging MVP

This is the only active product roadmap. Older gameplans, checklists, and
handoffs are historical evidence; they do not reopen completed work or restore
old priorities.

## P0 — make the verified MVP natural and reliable

### R1. Retrieval that works without prompt engineering

- replace the unsafe universal `min_relevance=0.78` behavior with a calibrated
  retrieval policy for the active embedding profile;
- add Portuguese and English cross-client regression cases;
- guarantee that a direct durable preference is returned for a direct query;
- retain meaningful abstention for unrelated queries; and
- make clients omit retrieval tuning parameters in normal use.

Acceptance: ChatGPT writes a synthetic preference and Gemini answers it with a
plain-language `@Umcp Cloud` prompt, without mentioning tool parameters.

### R2. Client-neutral capture and provenance

- stop hardcoding `source_model="chatgpt"` in `memory.capture`;
- derive safe client/source metadata from the authenticated MCP context where
  available;
- preserve explicit user intent and evidence without storing full conversation
  transcripts by default; and
- add conformance tests for ChatGPT and Gemini capture.

### R3. One clean end-to-end acceptance suite

- automate OAuth discovery, tool sync, write/capture, portal visibility, and
  cross-surface recall against one immutable staging SHA;
- record redacted reports for ChatGPT and Gemini;
- verify refresh, revoke, expiry, and owner isolation in the same release
  candidate; and
- make the report fail closed when evidence is missing.

## P1 — complete the private beta product

### B1. Login and connection experience

- replace the minimal OAuth handoff page with branded, accessible guidance;
- show connected clients, scopes, last synchronization, and revocation state;
- provide client-specific setup instructions without exposing owner IDs or
  secrets; and
- make OAuth errors actionable and safely redacted.

### B2. Memory portal controls

- add search, filtering, provenance, edit/correct, forget confirmation, and
  export;
- show when a memory was captured and which client supplied it;
- surface conflicts and superseded memories; and
- preserve server-owned authorization for every action.

### B3. Claude acceptance

- select one officially supported Claude surface;
- complete OAuth and the same owner-bound lifecycle journey;
- verify cross-surface recall with ChatGPT and Gemini; and
- mark Claude supported only after a dated report exists.

## P2 — readiness beyond the owner-only MVP

- production environment separation and migration policy;
- rate limits, abuse controls, operational SLOs, alerts, and incident process;
- backup/restore and deletion-retention acceptance on the release SHA;
- security review of OAuth, RLS, KMS, logs, exports, and portal controls;
- dependency and supply-chain release gates; and
- private-beta terms, privacy communication, support channel, and account
  deletion workflow.

## Explicitly deprioritized

The following do not block the current MVP:

- public marketplace publication;
- a broad open beta;
- PyPI/npm distribution;
- native mobile applications;
- autonomous consolidation or knowledge graphs;
- billing and team workspaces;
- “works everywhere” compatibility; and
- E2EE/zero-knowledge claims without a different reviewed architecture.

## Evidence policy

No roadmap checkbox or old handoff is a support claim. A capability moves to
verified only when the exact surface, date, deployed source SHA, and user
journey are recorded in [Current state](CURRENT_STATE.md) or a linked current
acceptance report.
