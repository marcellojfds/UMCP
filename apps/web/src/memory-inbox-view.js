import { escapeHtml } from "./view-utils.js";

function statusLabel(state) {
  return `<span class="status status--${escapeHtml(state)}">${escapeHtml(state)}</span>`;
}

function provenance(memory) {
  const source = memory.provenance || {};
  return `<dl class="metadata-grid"><div><dt>Source</dt><dd>${escapeHtml(source.source_client || "not provided")}</dd></div><div><dt>Origin</dt><dd>${escapeHtml(source.source_type || "not provided")}</dd></div><div><dt>Captured</dt><dd>${escapeHtml(source.captured_at || "not provided")}</dd></div><div><dt>Space</dt><dd>${escapeHtml(memory.space ?? "global")}</dd></div></dl>`;
}

function consent(memory) {
  const record = memory.capture_consent || {};
  return `<div class="inbox-detail"><p class="mono">CONSENT / RETENTION REASON</p><p><strong>${escapeHtml(record.mode || "not provided")}</strong> · ${escapeHtml(record.reason_code || "not provided")}</p><small>Consent ${escapeHtml(record.consent_id || "not provided")} · policy ${escapeHtml(record.policy_version || "not provided")}</small></div>`;
}

function actionButtons(memory) {
  const common = `data-memory-id="${escapeHtml(memory.id)}" data-expected-version="${escapeHtml(memory.version)}"`;
  if (memory.state === "candidate") return `<div class="card-actions"><button class="button" type="button" data-action="confirm" ${common}>Confirm candidate</button><button class="button button--quiet" type="button" data-action="discard" ${common}>Discard &amp; forget</button></div>`;
  if (memory.state === "confirmed") return `<div class="card-actions"><button class="button" type="button" data-action="pin" ${common}>Pin memory</button><button class="button button--quiet" type="button" data-action="stale" ${common}>Mark stale</button><button class="button button--dark" type="button" data-action="forget" ${common}>Forget</button></div>`;
  if (memory.state === "pinned") return `<div class="card-actions"><button class="button" type="button" data-action="unpin" ${common}>Unpin</button><button class="button button--quiet" type="button" data-action="stale" ${common}>Mark stale</button><button class="button button--dark" type="button" data-action="forget" ${common}>Forget</button></div>`;
  if (memory.state === "stale") return `<div class="card-actions"><button class="button" type="button" data-action="review" ${common}>Review → confirmed</button><button class="button button--dark" type="button" data-action="forget" ${common}>Forget</button></div>`;
  return "";
}

function memoryCard(memory) {
  const edit = memory.state === "candidate" ? `<label for="edit-${escapeHtml(memory.id)}">Optional edit before confirmation</label><textarea id="edit-${escapeHtml(memory.id)}" data-memory-edit="${escapeHtml(memory.id)}">${escapeHtml(memory.content)}</textarea>` : "";
  return `<article class="inbox-card" aria-labelledby="memory-${escapeHtml(memory.id)}"><div class="inbox-card__header"><div><p class="mono">${escapeHtml(memory.type)} · v${escapeHtml(memory.version)}</p><h3 id="memory-${escapeHtml(memory.id)}">${escapeHtml(memory.content)}</h3></div>${statusLabel(memory.state)}</div>${provenance(memory)}${consent(memory)}${edit}${actionButtons(memory)}</article>`;
}

function connectionPanel(connections = []) {
  const rows = connections.map((connection) => `<li><span><strong>${escapeHtml(connection.name)}</strong><small>${escapeHtml(connection.status)} · ${escapeHtml((connection.scopes || []).join(", "))}</small></span>${connection.status === "active" ? `<button class="button button--quiet" type="button" data-action="revoke" data-connection-id="${escapeHtml(connection.id)}">Revoke connection</button>` : statusLabel("revoked")}</li>`).join("");
  return `<section class="inbox-panel" aria-labelledby="connections-heading"><p class="eyebrow">Connection consent boundary</p><h2 id="connections-heading">Access can be revoked per client.</h2><p>Revoking <code>chatgpt-sim</code> does not revoke <code>claude-sim</code>. The server must check revocation before lookup or capture.</p><ul class="connection-list">${rows || "<li>No connections in this fixture.</li>"}</ul></section>`;
}

function recallPanel(recall) {
  if (!recall) return `<section class="inbox-panel" aria-labelledby="recall-heading"><div class="inbox-panel__header"><div><p class="eyebrow">Cross-space recall preview</p><h2 id="recall-heading">See why a memory was retrieved.</h2></div><button class="button" type="button" data-action="recall">Run Work → MBA recall</button></div><p>Explicit <code>include_spaces: ["MBA"]</code> is required. Candidates, stale memories and revoked connections are not silently treated as eligible.</p></section>`;
  if (!recall.memories?.length) return `<section class="inbox-panel" aria-labelledby="recall-heading"><p class="eyebrow">Recall result</p><h2 id="recall-heading">No eligible memories.</h2><p class="empty-copy">The query completed successfully with count 0. Candidate and stale states are excluded by default.</p></section>`;
  return `<section class="inbox-panel" aria-labelledby="recall-heading"><p class="eyebrow">Recall result · count ${escapeHtml(recall.count)}</p><h2 id="recall-heading">Returned with a safe reason.</h2>${recall.memories.map((item) => `<div class="recall-result"><p>${escapeHtml(item.memory?.content || "")}</p><dl class="metadata-grid"><div><dt>Reason retrieved</dt><dd><code>${escapeHtml(item.reason_retrieved)}</code></dd></div><div><dt>Source</dt><dd>${escapeHtml(item.memory?.provenance?.source_client || "not provided")}</dd></div><div><dt>Space</dt><dd>${escapeHtml(item.memory?.space ?? "global")}</dd></div></dl></div>`).join("")}</section>`;
}

function restorePanel(restore) {
  if (!restore) return "";
  return `<section class="inbox-panel restore-panel" aria-labelledby="restore-heading"><p class="eyebrow">Restore / import safety</p><h2 id="restore-heading">The forgotten ID remains blocked.</h2><p>Restore/import is not a lifecycle reversal. The content-free tombstone prevents the same memory ID from being recreated.</p><p class="action-result" role="status"><strong>${escapeHtml(restore.status)}</strong> · recreated: ${escapeHtml(restore.recreated)}</p></section>`;
}

/**
 * Render all Inbox states from public result data. No method here applies
 * policy; it only presents result fields supplied by the adapter.
 */
export function renderMemoryInbox({ state = "success", mode = "fixture", candidates = [], memories = [], connections = [], recall = null, restore = null } = {}) {
  if (state === "loading") return `<div class="empty-state inbox-state" data-state="loading" role="status"><span class="mono">LOADING MEMORY INBOX</span><p>Checking the public M1 result boundary…</p></div>`;
  if (state === "error") return `<div class="empty-state inbox-state" data-state="error" role="alert"><span class="mono">INBOX ERROR</span><p>We could not load the Inbox result. Retry when the M1 boundary is available.</p><button class="button button--dark" type="button" data-action="retry-inbox">Retry</button></div>`;
  const visibleMemory = memories.find((memory) => memory.state !== "candidate");
  const inboxContent = candidates.length ? `<div class="inbox-list">${candidates.map(memoryCard).join("")}</div>` : `<div class="empty-state inbox-state" data-state="empty"><span class="mono">INBOX EMPTY</span><p>No candidates are waiting for review. Confirmed, pinned and stale memories remain visible below.</p></div>`;
  const lifecycleContent = visibleMemory ? `<section class="inbox-panel" aria-labelledby="lifecycle-heading"><div class="inbox-panel__header"><div><p class="eyebrow">Lifecycle view</p><h2 id="lifecycle-heading">Review the same memory after confirmation.</h2></div>${statusLabel(visibleMemory.state)}</div>${memoryCard(visibleMemory)}</section>` : "";
  const tombstoneAction = restore ? "" : `<button class="button button--quiet" type="button" data-action="restore">Try restore/import of the fixture</button>`;
  return `<div class="inbox-experience" data-state="success" data-mode="${escapeHtml(mode)}"><div class="fixture-banner" role="note"><span class="mono">${mode === "fixture" ? "LOCAL CONTRACT FIXTURE" : "M1 MCP ADAPTER"}</span><p>${mode === "fixture" ? "Synthetic data only. This screen exercises frozen M1 result shapes before Core/M1-B integration." : "Connected through the public M1 adapter; tenant, owner, scopes and lifecycle policy remain server-owned."}</p><small>Integration boundary: <code>${escapeHtml(mode === "fixture" ? "fixture://m01-memory-inbox" : "/mcp")}</code></small></div><div class="inbox-toolbar"><div><p class="eyebrow">M01-C / Memory Inbox</p><h2>Review before recall.</h2><p class="lede">Candidates are not recalled until you confirm them. Provenance says where a memory came from; consent says why retention was allowed.</p></div><div class="inbox-summary" aria-label="Inbox summary"><strong>${escapeHtml(candidates.length)}</strong><span>candidate${candidates.length === 1 ? "" : "s"} waiting</span></div></div><section class="inbox-panel" aria-labelledby="candidates-heading"><div class="inbox-panel__header"><div><p class="eyebrow">Candidate queue</p><h2 id="candidates-heading">Consent before recall.</h2></div>${statusLabel("candidate")}</div>${inboxContent}</section>${lifecycleContent}${recallPanel(recall)}${connectionPanel(connections)}${restore ? restorePanel(restore) : `<section class="inbox-panel restore-panel" aria-labelledby="restore-heading"><p class="eyebrow">Forget / restore</p><h2 id="restore-heading">Terminal deletion stays terminal.</h2><p>After forget, a content-free tombstone blocks restoring the same memory ID.</p>${tombstoneAction}</section>`}<p id="inbox-action-status" class="action-result" role="status" aria-live="polite"></p></div>`;
}
