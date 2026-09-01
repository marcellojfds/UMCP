# Experiment 0001 — Autonomous Memory Capture, Obsidian-Style WikiLinks, and Knowledge Graph View

**Status:** Validated Prototype & Proposed Standard  
**Date:** 2026-08-31  
**Author:** Marcello Junqueira Franco / UMCP Core Team  

---

## 1. Context & Motivation

In previous versions, the UMCP Memory Vault displayed memories as isolated cards in a list or grid. While the backend vector database enabled semantic search, users lacked a mental model of how their thoughts, decisions, and preferences interconnect over time. Furthermore, user testing showed that expecting the user to explicitly command *"Save this in UMCP"* introduces friction that prevents daily habit formation.

This experiment implements two foundational capabilities:
1. **Autonomous Background Capture:** LLMs (ChatGPT, Claude, Gemini) connected via MCP proactively identify, structure, and store durable knowledge without requiring explicit save triggers.
2. **Obsidian-Style Cross-Linking & Interactive Knowledge Graph:** Memories are structured with `[[Entity]]` concepts and `#tags`, generating a navigable Knowledge Graph (Graph View 🕸️) and backlink network across all AI assistants.

---

## 2. Architecture & Design

### A. Autonomous Background Capture Pipeline

```
User Message ──► LLM Conversation Evaluator
                     │
                     ├─ Ephemeral chatter / greetings ──────────► [Ignored]
                     ├─ Secrets / Credentials / Temp code ─────► [Rejected / Filtered]
                     └─ Durable Context (Decision, Preference) ─► [memory.capture]
                                                                      │
                                                                      ▼
                                                          - Enclose [[Entities]]
                                                          - Assign Space (#dev, #work)
                                                          - Save to UMCP Vault
```

- **Server Instructions (`src/omp/server/official.py`):**
  The MCP server instructs agents to autonomously classify durable facts, extract central concepts into `[[Entity]]` format, and assign contextual spaces (`#work`, `#dev`, `#mba`, `#finance`).
- **Zero-Friction User Experience:** The user converses normally with their preferred AI, while the vault silently maintains continuity and cross-references in the background.

---

### B. Obsidian-Style WikiLinks & Entity Formatting

- **Syntax:** `[[Concept Name]]` and `#tag`.
- **Parsing (`apps/web/src/memory-vault-view.js`):**
  - `formatMemoryContent(content)` transforms `\[\[(.*?)\]\]` into interactive `.wikilink` components.
  - `extractWikilinks(content)` extracts unique concept nodes from raw memory strings.
- **User Action:** Clicking any `[[Concept]]` badge immediately triggers a filtered query across the vault for all memories referencing that concept.

---

### C. Connected Concepts & Backlink Inspector

- Inside **Memory Detail** (`#/memories/:id`):
  - Renders the full formatted content with highlighted WikiLinks.
  - Generates a **"Connected Concepts"** section displaying all referenced entity hubs as interactive navigation chips.

---

### D. Interactive Knowledge Graph View (🕸️)

- **View Switcher:** Added `🕸 Graph View` alongside `▦ Cards` and `☷ List` in the portal toolbar (`#/memories?view=graph`).
- **Graph Topology:**
  - **Concept Hubs (`[[...]]`):** High-degree golden nodes representing overarching topics.
  - **Memory Nodes:** Color-coded by semantic type:
    - 🟣 **Decision** (`#8b5cf6`)
    - 🔵 **Preference** (`#3b82f6`)
    - 🟢 **Lesson** (`#10b981`)
    - 💗 **Goal** (`#ec4899`)
    - 🔘 **Fact / Project Context** (`#64748b`)
  - **Arestas (Edges):** Dashed connecting lines between memories and their associated concept hubs.
- **Interactivity:**
  - Hover states show full text snippets, connection counts, and metadata.
  - Node clicks navigate directly to the specific memory or concept search.

---

## 3. Implemented Code Reference

| Component | File Path | Responsibility |
| :--- | :--- | :--- |
| **MCP Server Instructions** | `src/omp/server/official.py` | Autonomous capture guidelines & tool annotations |
| **Graph & WikiLink Parser** | `apps/web/src/memory-vault-view.js` | `formatMemoryContent`, `extractWikilinks`, `renderMemoryGraph` |
| **Portal Router** | `apps/web/src/app.js` | Route parsing for `view=graph` and preview auto-routing |
| **Graph Visuals** | `apps/web/src/styles.css` | `.vault-graph-container`, `.wikilink`, `.taglink`, `.graph-node` |
| **Preview Fixtures** | `apps/web/src/account-preview.js` | Interconnected mock dataset demonstrating graph relationships |

---

## 4. Future Roadmap & Enhancements

1. **Dynamic Force-Directed Simulation:** Integrate a canvas/WebGL physics engine (e.g. D3-force or Force-Graph) for drag-and-drop physics and 3D graph exploration with thousands of nodes.
2. **Graph RAG Traversal:** When an AI calls `memory.search("Projeto Alpha")`, the server can return not just the matched note, but a 1-hop graph neighborhood (all connected decisions, lessons, and constraints).
3. **Database Relation Tables:** Index explicit graph edges in Postgres (`memory_relations`) to compute clustering coefficients and centrality scores for the most influential concepts in a user's vault.
