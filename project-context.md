# Open Memory Protocol — Project Context

## 0. Purpose of this document

This document captures the current product thesis, architectural direction, constraints, open questions, and initial implementation ideas for an open-source project tentatively called **Open Memory Protocol (OMP)**.

Treat this as project context, **not as a final technical specification**.

Some architectural decisions remain intentionally open and should be challenged through prototypes.

---

# 1. Core problem

People increasingly use multiple LLMs and AI agents:

- ChatGPT
- Claude
- Gemini
- Codex
- IDE agents
- future AI systems

Important knowledge is generated inside these interactions.

Examples:

- personal preferences;
- facts about the user;
- decisions;
- project context;
- hypotheses;
- academic concepts;
- conclusions;
- lessons learned;
- recurring patterns;
- relationships between ideas.

Today this knowledge is fragmented across conversation histories and vendors.

A useful insight generated while studying an MBA case, for example, might be highly relevant months later while solving a business problem.

The current model may have no way of knowing that insight exists.

The fundamental hypothesis is:

> Long-term memory should be independent from the model and owned by the user.

---

# 2. Product vision

Build an open-source memory layer that can be connected to different LLMs through MCP.

The system should allow AI agents to:

1. identify knowledge worth remembering;
2. persist that knowledge;
3. retrieve relevant knowledge later;
4. update existing knowledge;
5. connect related knowledge;
6. forget or supersede obsolete knowledge;
7. periodically consolidate many memories into higher-level knowledge.

The desired result is not merely persistent context.

The long-term ambition is:

> **Accumulated intelligence across models and across time.**

---

# 3. Important distinction

OMP should NOT primarily be:

- conversation storage;
- chat history search;
- a giant RAG database;
- a vector database exposed through MCP;
- a dumping ground for every user message.

The system should attempt to transform interactions into **knowledge**.

A useful mental model is:

```text
conversation
    ↓
candidate memories
    ↓
structured memories
    ↓
relationships
    ↓
consolidation
    ↓
knowledge
```

---

# 4. Core system components

Current conceptual architecture:

```text
LLM / Agent
     │
     │ MCP
     ▼
┌──────────────────────┐
│ Open Memory Protocol │
└──────────────────────┘
     │
     ├── Memory Writer
     ├── Memory Retriever
     ├── Memory Store
     ├── Memory Consolidator
     └── Memory Lifecycle
```

---

# 5. Memory Writer

The writer determines what deserves to become memory.

It should avoid blindly storing conversations.

Potential memory categories:

```text
fact
preference
decision
insight
hypothesis
lesson
goal
project_context
concept
relationship
open_question
```

Example:

Conversation:

> After analyzing this case, I think marketplaces with strong local network effects should prioritize geographic density before geographic expansion.

Possible stored memory:

```json
{
  "type": "insight",
  "content": "For marketplaces with strong local network effects, geographic density may be more important than early geographic expansion.",
  "source_context": "MBA strategy discussion",
  "importance": 0.82,
  "confidence": 0.76
}
```

The exact schema is not final.

---

# 6. Memory writing philosophy

Do not store everything.

Potential pipeline:

```text
interaction
    ↓
candidate extraction
    ↓
importance evaluation
    ↓
deduplication
    ↓
contradiction / update detection
    ↓
persistence
```

An initial implementation may use an LLM to extract candidate memories and a more conservative validation step before persistence.

We should test whether this second validation step materially improves memory quality enough to justify its cost and latency.

---

# 7. Memory Retriever

Retrieval is arguably the most important part of the project.

Naive retrieval would be:

```text
current prompt
→ embedding
→ nearest vectors
```

OMP should aim beyond this.

The relevant question is not:

> Which memories look most similar to the current prompt?

It is:

> Which things this user previously learned, decided, experienced, or believed could materially improve the answer to the current problem?

Potential retrieval pipeline:

```text
current interaction
       ↓
intent understanding
       ↓
query generation
       ↓
candidate retrieval
       ↓
reranking
       ↓
relevance threshold
       ↓
context injection
```

Possible ranking signals:

```text
semantic similarity
importance
recency
confidence
memory type
project relevance
relationships
historical usefulness
contradiction state
```

A conceptual scoring function could begin as:

```text
relevance =
    semantic_similarity
  × contextual_relevance
  × importance
  × confidence
```

This is only a hypothesis.

---

# 8. Cross-domain retrieval

This is a core product hypothesis.

OMP becomes particularly valuable when it surfaces relevant knowledge across domains.

Example:

```text
MBA session
↓
user learns a concept about market structure
↓
memory stored

months later

work strategy discussion
↓
OMP recognizes conceptual relationship
↓
MBA insight is retrieved
↓
LLM applies it to the business problem
```

This behavior should become one of the project's primary evaluation cases.

Simple embedding similarity may not be sufficient.

Possible future approaches include:

- query expansion;
- LLM-based reranking;
- knowledge graphs;
- entity relationships;
- memory-to-memory links;
- abstraction layers.

---

# 9. Memory lifecycle

Memories should not necessarily be immutable.

Possible states:

```text
active
superseded
contradicted
archived
forgotten
```

A memory may:

- become more confident;
- lose relevance;
- receive supporting evidence;
- be contradicted;
- merge with another memory;
- become part of a higher-level insight.

Example:

```text
Memory A:
"I prefer X."

Later interaction:
"My preference has changed; I now prefer Y."

Expected behavior:

A should not simply coexist forever with B.

The system should understand that B potentially supersedes A.
```

---

# 10. Memory Consolidator

Long-term knowledge requires more than writing and retrieval.

A background process should periodically inspect memories.

Example:

```text
raw memories
     ↓
clusters
     ↓
patterns
     ↓
higher-order insight
```

For example:

```text
Memory 1
Memory 2
Memory 3
Memory 4
     ↓
Consolidator
     ↓
"Across several GTM experiments, personalization appears to improve meeting conversion primarily when it signals effort rather than monetary value."
```

This process could run:

- daily;
- weekly;
- after N new memories;
- on demand.

Important:

**MCP itself does not provide scheduling.**

Scheduled consolidation should be executed by external infrastructure such as:

- cron;
- worker queues;
- scheduled cloud jobs;
- GitHub Actions during early development.

---

# 11. MCP interface

The MCP surface should remain small and opinionated.

Initial candidate tools:

```text
memory.write
memory.search
memory.update
memory.related
memory.forget
```

Potential future tools:

```text
memory.explain
memory.consolidate
memory.history
```

Avoid exposing database primitives directly.

The MCP should expose **memory semantics**, not storage semantics.

Bad:

```text
vector.search()
database.insert()
```

Better:

```text
memory.search()
memory.write()
memory.forget()
```

---

# 12. Potential memory.search response

Search should eventually provide enough information for an agent to reason about whether to use a memory.

Example:

```json
{
  "memories": [
    {
      "id": "mem_123",
      "content": "...",
      "type": "insight",
      "confidence": 0.91,
      "importance": 0.84,
      "reason_retrieved": "Relevant to the user's current market-structure question."
    }
  ]
}
```

`reason_retrieved` may be useful for debugging and evaluation.

Whether it should exist in the production protocol remains open.

---

# 13. Storage

Initial preferred direction:

```text
FastAPI
PostgreSQL
pgvector
```

Qdrant remains a reasonable alternative.

Postgres + pgvector is attractive initially because structured metadata, lifecycle state, relationships, and vectors can live in one system.

Do not prematurely introduce multiple databases.

Potential future architecture:

```text
Postgres
 ├── memories
 ├── relationships
 ├── users
 ├── provenance
 └── embeddings
```

A dedicated graph database should only be introduced if experiments demonstrate a clear benefit.

---

# 14. Privacy model

This is a critical requirement.

The service should eventually support central hosting because requiring normal users to run infrastructure will significantly limit adoption.

However:

> The infrastructure operator should ideally not need access to readable user memories.

Current direction:

```text
client
  ↓
encrypt memory content
  ↓
server stores ciphertext
```

Possible architecture:

```text
CLIENT
 ├── plaintext
 ├── embedding generation
 └── encryption
        ↓
SERVER
 ├── encrypted content
 ├── vector
 └── minimal metadata
        ↓
CLIENT
 └── decrypt retrieved memories
```

Important caveat:

**Embeddings themselves can leak information.**

Therefore this architecture should not yet be described as perfect end-to-end privacy.

A proper threat model is required.

---

# 15. Privacy principles

Desired principles:

### User-owned keys

The server should ideally not possess the key required to decrypt memory content.

### Minimal plaintext metadata

Avoid unnecessary readable metadata.

### Portability

Users should be able to export their memories.

### No lock-in

The memory format should be open.

### Explicit threat model

Documentation should clearly explain:

```text
what the server can see
what the server cannot see
what an attacker could infer
what encryption protects
what embeddings potentially expose
```

Trust should come from architecture and transparency, not marketing claims.

---

# 16. Central hosting

The project should support two distinct concepts:

```text
Open-source protocol / server
+
optional managed hosting
```

Open source is important for:

- trust;
- experimentation;
- contributions;
- interoperability;
- adoption.

Managed hosting is important for:

- normal users;
- testing product hypotheses;
- lowering setup friction;
- collecting aggregate system-level performance metrics where privacy permits.

Self-hosting can exist, but it should not be required for ordinary users.

---

# 17. Memory spaces

We discussed possible logical memory spaces such as:

```text
personal
MBA
work
project X
```

However, **do not over-engineer cryptographic isolation per space at this stage.**

Logical namespaces may still be useful for retrieval and organization.

This remains an implementation detail to test.

---

# 18. Provenance

Every memory should ideally know where it came from.

Potential fields:

```text
source
source_model
source_conversation
created_at
updated_at
evidence
```

This enables questions such as:

```text
Why do we believe this?
When did this belief appear?
Has it changed?
Which interactions support it?
```

Provenance may become essential for trustworthy long-term memory.

---

# 19. Knowledge relationships

Long term, memories should probably form relationships.

Example:

```text
[market density insight]
        │
        ├── supports
        ▼
[regional GTM strategy]

[experiment result]
        │
        ├── contradicts
        ▼
[previous hypothesis]
```

Possible relationship types:

```text
supports
contradicts
derived_from
related_to
supersedes
applies_to
```

Start simple.

Do not introduce a graph database unless required.

Relationships can initially live in Postgres.

---

# 20. Evaluation

Memory systems are difficult to evaluate because successful retrieval is contextual.

We need an evaluation framework early.

Potential metrics:

### Write precision

Of memories stored, how many were actually worth remembering?

### Write recall

How many important memories were missed?

### Retrieval precision

Of memories retrieved, how many improved the answer?

### Retrieval recall

Did the system miss a memory that would have materially improved the answer?

### Intrusion rate

How often does OMP surface technically related but annoying or irrelevant memories?

This metric is particularly important.

Bad memory can be worse than no memory.

### Cross-domain discovery

Can the system identify useful relationships between knowledge created in different contexts?

### Consolidation quality

Do consolidated memories represent genuine abstractions rather than generic summaries?

---

# 21. Core design principle

Optimize for:

```text
useful memory
```

not:

```text
maximum memory
```

The system should be comfortable returning:

```text
no relevant memory
```

Retrieval precision may initially matter more than recall.

One irrelevant personal memory injected into an unrelated conversation can rapidly destroy user trust.

---

# 22. Suggested MVP

Avoid building the entire vision initially.

### MVP 0

Implement:

```text
memory.write
memory.search
memory.update
memory.forget
```

Stack:

```text
Python
FastAPI
Postgres
pgvector
MCP server
```

Basic memory schema.

Basic embedding retrieval.

No graph database.

No sophisticated consolidation.

No complex privacy architecture yet unless it is inexpensive to include.

Goal:

**Prove that persistent cross-model memory is useful.**

---

# 23. MVP 1

Add intelligent writing.

```text
conversation
↓
memory candidate extraction
↓
deduplication
↓
structured memory
```

Test memory quality.

---

# 24. MVP 2

Add intelligent retrieval.

```text
prompt
↓
intent
↓
multiple retrieval queries
↓
vector candidates
↓
reranking
↓
threshold
```

Focus strongly on avoiding irrelevant memory injection.

---

# 25. MVP 3

Add consolidation.

Create a scheduled worker that periodically turns clusters of memories into higher-level knowledge.

---

# 26. MVP 4

Explore privacy-preserving hosted architecture.

Prototype:

```text
client-side encryption
client-side or trusted embedding generation
central vector retrieval
client-side decryption
```

Perform threat-model review before making privacy claims.

---

# 27. Example end-to-end experience

User studies strategy:

```text
User:
"After discussing this case, I think this company should dominate one geographic market before expanding."

LLM:
develops the idea with the user

OMP:
stores the resulting insight
```

Months later:

```text
User:
"We are trying to decide whether our GTM team should attack many cities or dominate a few key regions."

OMP:
retrieves previous market-density insight

LLM:
"You previously reached a similar conclusion while studying market structure: when local density creates an advantage, dominating a region may be more valuable than maximizing geographic coverage..."
```

This is the kind of moment the product should create.

---

# 28. Important product question

The product is NOT successful merely because:

```text
memory was retrieved
```

It is successful when the user thinks:

> **"I had forgotten that I knew this."**

That should be one of the north-star qualitative experiences.

---

# 29. Open questions

Do not assume these are solved.

### Writing

Who decides what deserves memory?

- originating model?
- OMP model?
- deterministic rules?
- combination?

### Embeddings

Where are embeddings generated?

- client?
- server?
- user's LLM provider?

### Encryption

How can semantic search coexist with a strong privacy model?

### Retrieval

How much should be vector similarity versus reasoning?

### Consolidation

How aggressively should memories be abstracted?

### Forgetting

Should memories decay naturally?

### Contradictions

How should conflicting memories coexist?

### Cost

How much model inference can happen per interaction before OMP becomes too expensive?

### Latency

Should memory retrieval block every LLM response?

### MCP behavior

Should models be instructed to call memory proactively, or should OMP provide stronger orchestration?

---

# 30. Engineering principles

1. Keep the MCP interface small.
2. Separate memory semantics from storage implementation.
3. Do not store everything.
4. Prefer retrieval precision over aggressive recall.
5. Preserve provenance.
6. Make memory portable.
7. Design privacy explicitly.
8. Avoid premature infrastructure complexity.
9. Build evaluation alongside the product.
10. Treat memory as a lifecycle, not a CRUD table.

---

# 31. Repository direction

Possible initial structure:

```text
open-memory-protocol/
│
├── README.md
├── MANIFESTO.md
├── LICENSE
├── pyproject.toml
│
├── src/
│   └── omp/
│       ├── server/
│       ├── memory/
│       │   ├── writer.py
│       │   ├── retriever.py
│       │   ├── lifecycle.py
│       │   └── models.py
│       ├── storage/
│       │   ├── postgres.py
│       │   └── embeddings.py
│       ├── mcp/
│       │   └── tools.py
│       └── config.py
│
├── migrations/
├── tests/
├── evals/
└── docs/
    ├── architecture.md
    ├── memory-model.md
    ├── privacy.md
    └── retrieval.md
```

This is a suggestion, not a hard requirement.

---

# 32. First Codex objective

Before implementing significant infrastructure:

1. inspect the repository if one already exists;
2. understand the current state;
3. propose the smallest architecture capable of supporting MVP 0;
4. define the initial memory schema;
5. define the MCP tool contracts;
6. define an evaluation strategy;
7. identify privacy decisions that would be expensive to reverse later;
8. produce an implementation plan;
9. only then begin implementation.

Avoid prematurely implementing:

- graph databases;
- complex agents;
- multi-stage consolidation;
- elaborate UI;
- enterprise features.

The first milestone should demonstrate:

```text
Model A writes a useful memory
        ↓
memory persists
        ↓
Model B encounters a relevant problem
        ↓
OMP retrieves the memory
        ↓
Model B uses it correctly
```

If that experience is compelling, expand from there.

---

# 33. Working thesis

The deepest hypothesis behind this project is:

> **AI models will become increasingly interchangeable, but the accumulated context of a person's life will become increasingly valuable.**

Therefore the durable asset should not be the conversation.

It should be the memory built from those conversations.

And that memory should belong to the user.