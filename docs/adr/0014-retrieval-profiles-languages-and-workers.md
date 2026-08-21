# ADR 0014 — Retrieval profiles, languages and tenant-scoped workers

## Status

Accepted for productization design (2026-08-21).

## Decision

The frozen E5 candidate remains `intfloat/e5-small-v2` at its recorded pinned
revision, 384 dimensions, mean pooling, `query:`/`passage:` prefixes,
threshold `0.76`, candidate limit 50 and result limit 5. It is development
promotion eligible only. `hash/v1` stays as a compatible fallback and is never
called approved semantic retrieval.

Profiles are immutable tuples of model identifier, revision, dimension, metric,
pooling and preprocessing. Searches reject mixed profiles/dimensions/versions
and never return a stale vector. Embed and re-embed work uses tenant- and
principal-bound idempotent jobs with dedupe keys, bounded retry, DLQ,
backpressure and states `pending`, `ready`, `stale`, `failed`.

## Consequences

Portuguese and English development suites are independent of the sealed
holdout. Any multilingual candidate needs a separate ADR, preregistered corpus
and protocol. No execution can revise the frozen threshold or select a model
post hoc.
