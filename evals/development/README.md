# Verification development suites

These are synthetic, development-only protocol suites. English and Portuguese
are separate files and separate invocations; cases are never mixed. They test
the evaluation contract and safety expectations for:

- capture precision;
- candidate deduplication;
- contradiction;
- cross-space relevance;
- provenance;
- abstention;
- memory poisoning;
- prompt injection;
- stale memory;
- concepts.

`scripts/run-development-evals` is a deterministic contract harness. It does
not run a model, change E5, change threshold `0.76`, inspect a holdout, or make
a product-quality claim. Core-backed metrics remain pending the matching
`M<id>-INTEGRATED.md` candidate handoff and the frozen protocol.

Example:

```sh
scripts/run-development-evals --language en --output /tmp/umcp-evals-en.json
scripts/run-development-evals --language pt --output /tmp/umcp-evals-pt.json
```
