# ADR 0009 — Community and Cloud editions share one core

## Status

Accepted for productization design (2026-08-21).

## Decision

UMCP has two compositions, not two domains:

| Edition | Boundary | Transport | Identity |
| --- | --- | --- | --- |
| Community | trusted local operator | stdio; optional local HTTP | local operator-selected `owner_id` compatibility |
| UMCP Cloud | untrusted internet clients | HTTPS Streamable HTTP at `/mcp` | verified principal and tenant only |

`MemoryApplicationService` remains the sole business-logic façade. Gateways,
web APIs and workers adapt verified commands to that façade; they must not
implement lifecycle, retrieval, authorization decisions, or repository writes
independently. The existing `owner_id` schema is local-compatibility only and
is never an authorization boundary in Cloud.

## Consequences

Cloud-specific adapters may require a principal and tenant context while the
Community adapter retains documented backward compatibility. Shared domain
types must gain tenant-aware equivalents incrementally, with migration tests.
Community remains self-hosted and makes no hosted security claims.
