# Retrieval-v0 relevance rubric

Apply labels using the query, its filters, the episode context, and the memory
state. Judge whether returning the memory helps answer the query, not whether
two strings share tokens.

| Grade | Meaning | Retrieval implication |
| --- | --- | --- |
| 2 | Direct, current evidence that answers the requested decision, fact, or preference. | Relevant. |
| 1 | Supporting evidence that is useful but less direct, incomplete, or contextual. | Relevant. |
| 0 | Does not answer the request, is a lexical/intent hard negative, belongs to a different owner/split, or is obsolete for a current request. | Intrusion if returned where the query expects abstention or excludes it. |

## Decision rules

- Respect `owner_id`, `split`, and explicit filters before semantic similarity.
  A cross-owner or cross-split record is grade 0 even when its content fits.
- For current recommendations, active replacements receive grade 2. A
  superseded, contradicted, or archived predecessor is grade 0 unless a future
  query explicitly asks for historical context.
- Cross-domain cases are grade 2 only when the memory's operating principle
  materially transfers to the target decision. Shared nouns alone are not
  enough.
- For an `abstain` query, there must be no positive label. Paired grade-0
  records identify plausible but wrong retrievals; do not invent a positive
  answer from nearby vocabulary.
- A grade 1 result may support a grade 2 result but cannot turn a negative
  query into a retrieval case.

## Adjudication protocol

Reviewers should label independently, record a concise reason, and resolve
disagreement by citing the above rule. Changing a label after freeze requires a
new dataset revision and a note of the affected query/memory IDs; it must not
be used to tune the baseline retrospectively. LLM-as-judge is not evidence for
the Alpha Gate B baseline.
