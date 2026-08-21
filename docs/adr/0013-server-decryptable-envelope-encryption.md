# ADR 0013 — Server-decryptable envelope encryption and honest claims

## Status

Accepted for productization design; KMS provider selection is pending
authorization (2026-08-21).

## Decision

Cloud v1 is server-decryptable. Content and provenance are application-layer
AEAD ciphertext with associated data binding tenant, table/field, record ID,
key version and schema version. Each tenant has a versioned DEK wrapped by a
KMS/HSM-held KEK. KMS failure, authentication failure, unavailable key version
and ciphertext swapped across tenants fail closed. Rotation rewraps DEKs; data
rewrites are explicit, resumable jobs. Secrets reside only in a secret manager.

Vectors are sensitive but remain indexable pgvector data: they receive RLS,
access controls and storage/backup encryption, not a false E2EE claim.
Break-glass access is time bounded, justified and audit logged. Exports may be
encrypted and have temporary download URLs; backups are encrypted, inventoried
and subject to tombstone reapplication.

## Claims

Do not claim E2EE, zero knowledge, universal encryption, or operator
inaccessibility. “Per-tenant encrypted content” is prohibited until ciphertext,
swap, rotation, KMS-failure and restore tests pass in staging.
