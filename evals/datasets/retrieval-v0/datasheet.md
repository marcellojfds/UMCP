# Datasheet — retrieval-v0

## Purpose and boundary

This is the Alpha v0 synthetic corpus used to evaluate retrieval without
collecting personal conversations. It was authored and frozen before tuning.
It tests useful retrieval, abstention, owner/split isolation, lifecycle
handling, cross-domain recall, and lexical hard negatives. It is not a
representative sample of production users and cannot establish safety or real
world quality by itself.

## Composition

| Artifact | Development | Holdout | Total |
| --- | ---: | ---: | ---: |
| Episodes | 20 | 5 | 25 |
| Memories | 100 | 25 | 125 |
| Queries | 40 | 10 | 50 |
| `retrieve` / positive behavior | 28 | 7 | 35 |
| `abstain` / negative behavior | 12 | 3 | 15 |
| Cross-domain queries | 8 | 2 | 10 |

Each episode has one synthetic owner, one space, five memories, and two
queries. No episode crosses a split. Memories include 75 active, 25 archived,
13 superseded and 12 contradicted records; types span insight, lesson, fact,
decision, preference and open question. The 25 spaces cover distinct fictional
domains.

The canonical MBA scenario is episode 01: market density is the strategic
insight, and a narrow-city launch is the current decision. Its cross-domain
query asks a marketplace GTM question rather than repeating the memory text.

## Record schemas

`memories.jsonl` has exactly: `memory_id`, `episode_id`, `split`, `owner_id`,
`space`, `type`, `state`, `content`, `importance`, `confidence`, `provenance`.
The synthetic provenance object contains `source_type`, `source_id`, and
`note`.

`queries.jsonl` has exactly: `query_id`, `episode_id`, `split`, `owner_id`,
`query`, `filters`, `kind`, `expected_behavior`. `kind` identifies positive,
negative, cross-domain, or hard-negative challenge shape; `expected_behavior`
is the gate-facing `retrieve` or `abstain` expectation.

`relevance.jsonl` has exactly `query_id`, `memory_id`, `grade`, `reason`.
Grades are 0, 1, or 2 as defined in the rubric. Every retrieval query has a
positive label and every abstention query has only grade-0 labels.

## Labeling and known limits

Grade 2 is direct current evidence; grade 1 is supporting but indirect; grade
0 is irrelevant, obsolete, or a deliberate hard negative. S03 manually
reviewed every query-memory label against the episode context. The corpus
deliberately labels archived/superseded/contradicted material as non-current;
future runner work must separately test whether state filters were supplied.

Hard-negative prompts use policy-like vocabulary while their paired memory is
about a different policy-shaped topic. Cross-domain labels test transferable
operating principles, not string matching. These judgment calls are limited by
the small synthetic sample and should receive independent label review before
Gate B. No LLM judge contributed labels.

## Privacy, retention, and access

All names, owners, organizations, events and text are invented. The corpus
contains no real personal data, secrets, credentials, contact details, or
customer data. It is versioned in the workspace as a low-sensitivity eval
artifact, consistent with `docs/privacy.md` and threat T12. Do not replace
synthetic fields with logs, exports, or user content.

## Versioning and reproducibility

Version: `retrieval-v0`. SHA-256 values in `checksums.json` apply to exact file
bytes. The validator checks schemas, IDs, episode ownership/splits, labels,
required totals, holdout shape and checksums. Any content or label correction
must create a new corpus version instead of changing this frozen dataset for a
better score.
