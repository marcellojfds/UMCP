# Public claim gate

Use this table in landing copy, docs, demos, and social metadata. A design ADR is not implementation evidence.

| Copy | Status now | Evidence required before use |
| --- | --- | --- |
| “User-controlled memory” | Not enabled for Cloud | End-to-end inspect, correct, export, delete, and revoke journeys |
| “Encrypted in transit and at rest” | Not enabled | TLS and storage/backup verification in authorized staging |
| “Memory content is encrypted with per-tenant keys” | Not enabled | Ciphertext-at-rest, swap, rotation, KMS failure, and restore tests |
| “End-to-end encrypted” / “zero knowledge” | Prohibited in v1 | A materially different architecture and independent audit |
| “Everything is encrypted” | Prohibited | It is inaccurate for metadata and indexable vectors |
| “Works everywhere” | Prohibited | Surface-specific conformance evidence, never a blanket badge |
| “Compatible” | Conditional | Protocol compatibility only; distinguish from tested integration |
| “Supported” | Conditional | Authenticated write → search → update → forget report for this exact surface/version |

Cloud v1 is designed to be server-decryptable for retrieval. Do not imply that
operators cannot access plaintext. See the [hosted threat model](../threat-model-hosted-v1.md).
