import { escapeHtml } from "./view-utils.js";

export function memoryStateLabel(state) {
  return ({
    candidate: "Needs review",
    confirmed: "Confirmed",
    pinned: "Pinned",
    stale: "Needs review",
    active: "Active",
    archived: "Archived",
    contradicted: "Conflict",
    superseded: "Superseded",
  })[state] || state || "Memory";
}

export function formatMemoryContent(content = "") {
  const escaped = escapeHtml(content);
  return escaped
    .replace(/\[\[(.*?)\]\]/g, (_, entity) => `<span class="wikilink" title="Connected concept"><span>[[</span><strong>${entity}</strong><span>]]</span></span>`)
    .replace(/(^|\s)#([\wÀ-ÿ-]+)/g, (_, prefix, tag) => `${prefix}<span class="taglink">#${tag}</span>`);
}

export function extractWikilinks(content = "") {
  const matches = [...String(content).matchAll(/\[\[(.*?)\]\]/g)];
  return [...new Set(matches.map((m) => m[1].trim()).filter(Boolean))];
}

export function memoryCard(memory) {
  const space = memory.space || "General";
  const type = memory.type || memory.memory_type || "memory";
  return `<article class="vault-memory-card"><div class="vault-memory-card__meta"><span class="memory-type">${escapeHtml(type)}</span><span class="memory-state memory-state--${escapeHtml(memory.state || "active")}">${escapeHtml(memoryStateLabel(memory.state))}</span></div><a class="vault-memory-card__content" href="#/memories/${encodeURIComponent(memory.id)}">${formatMemoryContent(memory.content)}</a><footer><span>${escapeHtml(space)}</span><span>v${escapeHtml(memory.version || 1)}</span></footer></article>`;
}

export function filterMemories(items, { space = "", state = "", type = "" } = {}) {
  return items.filter((memory) => {
    const memoryType = memory.type || memory.memory_type || "memory";
    return (!space || memory.space === space) && (!state || memory.state === state) && (!type || memoryType === type);
  });
}

function options(values, selected) {
  return values.map((value) => `<option value="${escapeHtml(value)}"${value === selected ? " selected" : ""}>${escapeHtml(value)}</option>`).join("");
}

export function renderMemoryGraph(items = []) {
  if (!items.length) return '<div class="vault-empty vault-empty--wide"><span>🕸</span><h2>No memories to map</h2><p>Capture memories to visualize their connections.</p></div>';

  const conceptMap = new Map();
  const nodes = [];
  const edges = [];

  items.forEach((m) => {
    const memoryNodeId = `mem_${m.id}`;
    const cleanContent = (m.content || "").replace(/\[\[(.*?)\]\]/g, "$1");
    const shortLabel = cleanContent.length > 28 ? cleanContent.slice(0, 26) + "…" : cleanContent;
    nodes.push({
      id: memoryNodeId,
      rawId: m.id,
      label: shortLabel,
      fullContent: m.content,
      type: m.type || m.memory_type || "fact",
      space: m.space || "General",
      kind: "memory",
      degree: 0,
    });

    const wikilinks = extractWikilinks(m.content);
    wikilinks.forEach((concept) => {
      if (!conceptMap.has(concept)) {
        conceptMap.set(concept, {
          id: `concept_${concept}`,
          label: concept,
          kind: "concept",
          degree: 0,
        });
      }
      const cNode = conceptMap.get(concept);
      cNode.degree += 1;
      const memNode = nodes.find((n) => n.id === memoryNodeId);
      if (memNode) memNode.degree += 1;
      edges.push({ source: memoryNodeId, target: cNode.id });
    });
  });

  conceptMap.forEach((cNode) => {
    nodes.push(cNode);
  });

  const width = 840;
  const height = 480;
  const cx = width / 2;
  const cy = height / 2;

  let conceptIdx = 0;
  let memIdx = 0;
  nodes.forEach((node) => {
    if (node.kind === "concept") {
      const angle = (conceptIdx / Math.max(1, conceptMap.size)) * 2 * Math.PI;
      const radius = 100 + (conceptIdx % 2) * 35;
      node.x = cx + radius * Math.cos(angle);
      node.y = cy + radius * Math.sin(angle);
      conceptIdx += 1;
    } else {
      const angle = (memIdx / Math.max(1, items.length)) * 2 * Math.PI;
      const radius = 210 + (memIdx % 3) * 35;
      node.x = cx + radius * Math.cos(angle);
      node.y = cy + radius * Math.sin(angle);
      memIdx += 1;
    }
  });

  const nodeMap = new Map(nodes.map((n) => [n.id, n]));

  const renderedEdges = edges.map((e) => {
    const s = nodeMap.get(e.source);
    const t = nodeMap.get(e.target);
    if (!s || !t) return "";
    return `<line class="graph-edge" x1="${s.x.toFixed(1)}" y1="${s.y.toFixed(1)}" x2="${t.x.toFixed(1)}" y2="${t.y.toFixed(1)}" />`;
  }).join("");

  const colorForType = (type) => ({
    decision: "#8b5cf6",
    preference: "#3b82f6",
    lesson: "#10b981",
    goal: "#ec4899",
    open_question: "#eab308",
    project_context: "#06b6d4",
  })[type] || "#64748b";

  const renderedNodes = nodes.map((n) => {
    if (n.kind === "concept") {
      return `<g class="graph-node graph-node--concept" transform="translate(${n.x.toFixed(1)}, ${n.y.toFixed(1)})" data-concept="${escapeHtml(n.label)}">
        <circle r="16" fill="#fff" stroke="#c45b2b" stroke-width="2.5" />
        <circle r="6" fill="#c45b2b" />
        <a href="#/memories?query=${encodeURIComponent(n.label)}"><text y="28" text-anchor="middle" class="graph-label graph-label--concept">[[${escapeHtml(n.label)}]]</text></a>
        <title>Concept Hub: ${escapeHtml(n.label)} (${n.degree} connections)</title>
      </g>`;
    }
    const color = colorForType(n.type);
    return `<g class="graph-node graph-node--memory" transform="translate(${n.x.toFixed(1)}, ${n.y.toFixed(1)})" data-memory-id="${escapeHtml(n.rawId)}">
      <circle r="12" fill="#fff" stroke="${color}" stroke-width="2" />
      <circle r="5" fill="${color}" />
      <a href="#/memories/${encodeURIComponent(n.rawId)}"><text y="24" text-anchor="middle" class="graph-label">${escapeHtml(n.label)}</text></a>
      <title>${escapeHtml(n.fullContent)} (${n.space} · ${n.type})</title>
    </g>`;
  }).join("");

  return `<div class="vault-graph-container">
    <div class="vault-graph-canvas">
      <svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid meet" class="vault-graph-svg" aria-label="Knowledge Graph">
        <g class="graph-edges">${renderedEdges}</g>
        <g class="graph-nodes">${renderedNodes}</g>
      </svg>
    </div>
    <footer class="vault-graph-legend">
      <div class="graph-legend-item"><span class="legend-dot" style="background:#c45b2b;"></span><span>Concept Hub ([[...]])</span></div>
      <div class="graph-legend-item"><span class="legend-dot" style="background:#8b5cf6;"></span><span>Decision</span></div>
      <div class="graph-legend-item"><span class="legend-dot" style="background:#3b82f6;"></span><span>Preference</span></div>
      <div class="graph-legend-item"><span class="legend-dot" style="background:#10b981;"></span><span>Lesson</span></div>
      <div class="graph-legend-item"><span class="legend-dot" style="background:#ec4899;"></span><span>Goal</span></div>
      <div class="graph-legend-item"><span class="legend-dot" style="background:#64748b;"></span><span>Fact / Context</span></div>
    </footer>
  </div>`;
}

export function renderMemoryBrowser({ items, query = "", space = "", state = "", type = "", view = "cards" }) {
  const spaces = [...new Set(items.map((memory) => memory.space).filter(Boolean))].sort();
  const states = [...new Set(items.map((memory) => memory.state).filter(Boolean))].sort();
  const types = [...new Set(items.map((memory) => memory.type || memory.memory_type).filter(Boolean))].sort();
  const visible = filterMemories(items, { space, state, type });
  const activeFilters = [space, state, type].filter(Boolean).length;
  const isGraph = view === "graph";
  const isList = view === "list";
  const params = new URLSearchParams();
  if (query) params.set("query", query);
  if (state) params.set("state", state);
  if (type) params.set("type", type);
  if (view && view !== "cards") params.set("view", view);
  const spaceHash = (value) => {
    const next = new URLSearchParams(params);
    if (value) next.set("space", value);
    const suffix = next.toString();
    return `#/memories${suffix ? `?${suffix}` : ""}`;
  };
  const count = `${visible.length}${visible.length !== items.length ? ` of ${items.length}` : ""} ${visible.length === 1 ? "memory" : "memories"}`;
  const chips = `<a class="filter-chip${space ? "" : " is-active"}" href="${spaceHash("")}"${space ? "" : ' aria-current="true"'}>All spaces</a>${spaces.map((value) => `<a class="filter-chip${space === value ? " is-active" : ""}" href="${spaceHash(value)}"${space === value ? ' aria-current="true"' : ""}>${escapeHtml(value)}</a>`).join("")}`;
  const filters = `<form class="vault-advanced-filters" data-memory-filters${activeFilters ? "" : " hidden"}><label>State<select name="state"><option value="">Any state</option>${options(states, state)}</select></label><label>Type<select name="type"><option value="">Any type</option>${options(types, type)}</select></label><div class="vault-filter-actions"><button class="button button--dark" type="submit">Apply filters</button><a href="#/memories${query ? `?query=${encodeURIComponent(query)}` : ""}">Clear</a></div></form>`;
  const empty = `<div class="vault-empty vault-empty--wide"><span>⌕</span><h2>${query || activeFilters ? "No matching memories" : "Your memory vault is empty"}</h2><p>${query || activeFilters ? "Try a different search or clear the active filters." : "Once an authorized assistant captures a memory, it will appear here with its origin and lifecycle."}</p>${query || activeFilters ? '<a class="button button--dark" href="#/memories">Clear search and filters</a>' : ""}</div>`;
  const filterbar = items.length || query || activeFilters ? `<div class="vault-filterbar"><span aria-live="polite">${count}</span>${chips}<button type="button" class="filter-chip${activeFilters ? " is-active" : ""}" data-toggle-filters aria-expanded="${activeFilters ? "true" : "false"}">Filters${activeFilters ? ` (${activeFilters})` : ""} <span aria-hidden="true">＋</span></button></div>${filters}` : "";
  const body = isGraph
    ? renderMemoryGraph(visible)
    : `<section class="vault-memory-grid${isList ? " is-list" : ""}" aria-label="Memories">${visible.length ? visible.map(memoryCard).join("") : empty}</section>`;
  return {
    content: `${filterbar}${body}`,
    toolbar: items.length || query || activeFilters ? `<div class="account-page-actions" aria-label="Memory view"><a class="icon-button${view === "cards" ? " is-active" : ""}" href="${memoryViewHash({ query, space, state, type, view: "cards" })}" aria-label="Card view"${view === "cards" ? ' aria-current="true"' : ""}>▦</a><a class="icon-button${view === "list" ? " is-active" : ""}" href="${memoryViewHash({ query, space, state, type, view: "list" })}" aria-label="List view"${view === "list" ? ' aria-current="true"' : ""}>☷</a><a class="icon-button${view === "graph" ? " is-active" : ""}" href="${memoryViewHash({ query, space, state, type, view: "graph" })}" aria-label="Graph view"${view === "graph" ? ' aria-current="true"' : ""}>🕸</a></div>` : "",
  };
}

export function memoryViewHash({ query = "", space = "", state = "", type = "", view = "cards" } = {}) {
  const params = new URLSearchParams();
  if (query) params.set("query", query);
  if (space) params.set("space", space);
  if (state) params.set("state", state);
  if (type) params.set("type", type);
  if (view && view !== "cards") params.set("view", view);
  const suffix = params.toString();
  return `#/memories${suffix ? `?${suffix}` : ""}`;
}

export function renderAccountInbox(items = []) {
  const reviewStates = new Set(["candidate", "stale", "contradicted"]);
  const review = items.filter((memory) => reviewStates.has(memory.state));
  if (!review.length) {
    return `<section class="vault-panel inbox-review" aria-labelledby="inbox-review-heading"><header><div><p class="account-eyebrow">Review queue</p><h2 id="inbox-review-heading">You are all caught up.</h2></div><span class="inbox-count">0</span></header><div class="vault-empty"><span>✓</span><h3>No memories need attention</h3><p>Candidates, stale memories, and conflicts will appear here when they need a decision.</p></div></section>`;
  }
  return `<section class="vault-panel inbox-review" aria-labelledby="inbox-review-heading"><header><div><p class="account-eyebrow">Review queue</p><h2 id="inbox-review-heading">${review.length} ${review.length === 1 ? "memory needs" : "memories need"} your attention.</h2><p>Open a memory to review its content, state, and origin in context.</p></div><span class="inbox-count">${review.length}</span></header><div class="vault-memory-list">${review.map(memoryCard).join("")}</div></section>`;
}

export function renderKeyConcepts(items = []) {
  if (!items.length) {
    return `<div class="vault-empty vault-empty--wide">
      <span>💡</span>
      <h2>Nenhum conceito estruturado ainda</h2>
      <p>Conforme seus assistentes capturam pensamentos, decisões e aprendizados com <code>[[Conceitos]]</code> ou espaços temáticos, eles serão automaticamente agrupados e sintetizados aqui.</p>
      <a class="button button--dark" href="#/memories">Explorar o cofre</a>
    </div>`;
  }

  const clusters = new Map();

  const addClusterMemory = (conceptName, memory, isExplicit = true) => {
    const key = conceptName.trim();
    if (!key) return;
    if (!clusters.has(key)) {
      clusters.set(key, {
        name: key,
        memories: [],
        typeCounts: {},
        spaces: new Set(),
        isExplicitWiki: isExplicit,
      });
    }
    const cluster = clusters.get(key);
    if (!cluster.memories.some((m) => m.id === memory.id)) {
      cluster.memories.push(memory);
      const type = memory.type || memory.memory_type || "fact";
      cluster.typeCounts[type] = (cluster.typeCounts[type] || 0) + 1;
      if (memory.space) cluster.spaces.add(memory.space);
    }
  };

  items.forEach((memory) => {
    const content = memory.content || "";
    const wikilinks = extractWikilinks(content);
    const tags = [...content.matchAll(/(?:^|\s)#([\wÀ-ÿ-]+)/g)].map((m) => m[1]);

    if (wikilinks.length) {
      wikilinks.forEach((concept) => addClusterMemory(concept, memory, true));
    }
    if (tags.length) {
      tags.forEach((tag) => addClusterMemory(tag, memory, false));
    }
    if (!wikilinks.length && !tags.length) {
      const spaceName = memory.space ? memory.space.charAt(0).toUpperCase() + memory.space.slice(1) : "General";
      addClusterMemory(spaceName, memory, false);
    }
  });

  const sortedClusters = [...clusters.values()].sort((a, b) => b.memories.length - a.memories.length);

  const clusterCards = sortedClusters.map((cluster) => {
    const decisions = cluster.memories.filter((m) => (m.type || m.memory_type) === "decision");
    const insights = cluster.memories.filter((m) => (m.type || m.memory_type) === "insight");
    const lessons = cluster.memories.filter((m) => (m.type || m.memory_type) === "lesson");

    let executiveSummary = "";
    if (decisions.length) {
      const latestDec = decisions[0];
      executiveSummary = `<strong>Decisão ativa:</strong> ${escapeHtml(latestDec.content.replace(/\[\[(.*?)\]\]/g, "$1"))}`;
    } else if (insights.length) {
      const latestIns = insights[0];
      executiveSummary = `<strong>Insight central:</strong> ${escapeHtml(latestIns.content.replace(/\[\[(.*?)\]\]/g, "$1"))}`;
    } else if (lessons.length) {
      const latestLes = lessons[0];
      executiveSummary = `<strong>Lição prática:</strong> ${escapeHtml(latestLes.content.replace(/\[\[(.*?)\]\]/g, "$1"))}`;
    } else {
      const latest = cluster.memories[0];
      executiveSummary = `${escapeHtml(latest.content.replace(/\[\[(.*?)\]\]/g, "$1"))}`;
    }

    const typeBadges = Object.entries(cluster.typeCounts)
      .map(([type, count]) => `<span class="concept-type-badge concept-type-badge--${escapeHtml(type)}">${count} ${escapeHtml(type)}</span>`)
      .join("");

    const spacesList = [...cluster.spaces].map((s) => `#${s}`).join(" ");

    const memoryListItems = cluster.memories.slice(0, 3).map((m) => {
      const t = m.type || m.memory_type || "memory";
      return `<li class="concept-memory-item">
        <span class="memory-type memory-type--compact">${escapeHtml(t)}</span>
        <a href="#/memories/${encodeURIComponent(m.id)}">${formatMemoryContent(m.content)}</a>
      </li>`;
    }).join("");

    const moreNotice = cluster.memories.length > 3
      ? `<p class="concept-more"><a href="#/memories?query=${encodeURIComponent(cluster.name)}">+${cluster.memories.length - 3} mais pensamentos neste conceito</a></p>`
      : "";

    return `<article class="concept-atlas-card">
      <header class="concept-card-header">
        <div class="concept-card-title">
          <span class="concept-icon">💡</span>
          <h3>[[${escapeHtml(cluster.name)}]]</h3>
          ${spacesList ? `<span class="concept-spaces">${escapeHtml(spacesList)}</span>` : ""}
        </div>
        <div class="concept-meta">
          <span class="concept-count">${cluster.memories.length} ${cluster.memories.length === 1 ? "pensamento" : "pensamentos"}</span>
        </div>
      </header>
      <div class="concept-summary">
        ${executiveSummary}
      </div>
      <div class="concept-badges">
        ${typeBadges}
      </div>
      <ul class="concept-memory-list">
        ${memoryListItems}
      </ul>
      ${moreNotice}
      <footer class="concept-card-footer">
        <a class="button button--quiet" href="#/memories?query=${encodeURIComponent(cluster.name)}&view=graph">Ver no Grafo 🕸️</a>
        <a class="button button--quiet" href="#/memories?query=${encodeURIComponent(cluster.name)}">Ver notas →</a>
      </footer>
    </article>`;
  }).join("");

  return `<section class="concept-atlas" aria-label="Atlas de Conceitos">
    <div class="concept-atlas-grid">
      ${clusterCards}
    </div>
  </section>`;
}
