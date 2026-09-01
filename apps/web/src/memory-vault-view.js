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

export function renderMemoryBrowser({ items, query = "", space = "", state = "", type = "", view = "cards" }) {
  const spaces = [...new Set(items.map((memory) => memory.space).filter(Boolean))].sort();
  const states = [...new Set(items.map((memory) => memory.state).filter(Boolean))].sort();
  const types = [...new Set(items.map((memory) => memory.type || memory.memory_type).filter(Boolean))].sort();
  const visible = filterMemories(items, { space, state, type });
  const activeFilters = [space, state, type].filter(Boolean).length;
  const params = new URLSearchParams();
  if (query) params.set("query", query);
  if (state) params.set("state", state);
  if (type) params.set("type", type);
  if (view === "list") params.set("view", "list");
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
  return {
    content: `${filterbar}<section class="vault-memory-grid${view === "list" ? " is-list" : ""}" aria-label="Memories">${visible.length ? visible.map(memoryCard).join("") : empty}</section>`,
    toolbar: items.length || query || activeFilters ? `<div class="account-page-actions" aria-label="Memory view"><a class="icon-button${view === "cards" ? " is-active" : ""}" href="${memoryViewHash({ query, space, state, type, view: "cards" })}" aria-label="Card view"${view === "cards" ? ' aria-current="true"' : ""}>▦</a><a class="icon-button${view === "list" ? " is-active" : ""}" href="${memoryViewHash({ query, space, state, type, view: "list" })}" aria-label="List view"${view === "list" ? ' aria-current="true"' : ""}>☷</a></div>` : "",
  };
}

export function memoryViewHash({ query = "", space = "", state = "", type = "", view = "cards" } = {}) {
  const params = new URLSearchParams();
  if (query) params.set("query", query);
  if (space) params.set("space", space);
  if (state) params.set("state", state);
  if (type) params.set("type", type);
  if (view === "list") params.set("view", "list");
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
