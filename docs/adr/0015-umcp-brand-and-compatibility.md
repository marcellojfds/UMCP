# ADR 0015 — UMCP brand and compatibility policy

## Status

Accepted for productization design (2026-08-21).

## Decision

The public working name is **UMCP — Open Memory Protocol**. The Python
namespace `omp` and MCP v0 contracts remain during productization; aliases and
deprecations replace destructive renames. Compatibility is stated by client
surface, version/date, transport, auth flow, tool/scopes, destructive-action
behavior, recipe and report—not by generic logos or “works everywhere” claims.

## Consequences

Domain, registry and trademark availability require research before any
exclusivity claim. A tested compatibility matrix is a release artifact. Consumer
web/mobile clients without a verified official integration are explicitly
unsupported rather than inferred from MCP support.
