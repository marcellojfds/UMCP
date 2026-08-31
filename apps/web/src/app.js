import { getAdminAdapter } from "./admin-adapter.js";
import { getAuthAdapter } from "./auth-fixture.js";
import { getMemoryInboxAdapter } from "./memory-inbox-adapter.js";
import { renderMemoryInbox } from "./memory-inbox-view.js";
import { M1_FIXTURE_MEMORY_ID } from "./memory-inbox-contract.js";
import { renderAccountShell } from "./account-shell.js";

const surfaces = [
  ["ChatGPT developer mode", "Remote /mcp or private test tunnel", "Unverified"],
  ["OpenAI Responses API", "Authenticated remote MCP", "Unverified"],
  ["Claude API", "Remote MCP connector", "Unverified"],
  ["Claude Desktop / Code", "Local stdio or remote where documented", "Unverified"],
  ["Gemini CLI", "Local configuration or remote where documented", "Unverified"],
  ["Gemini consumer web / mobile", "No verified official path", "Unverified"],
  ["Own agents", "Python / TypeScript SDK or MCP", "Experimental"],
];

const routePages = {
  "/inbox": ["Memory Inbox", "Review what is waiting for your consent.", "The M1 Inbox fixture is available without a server session. A deployed adapter can replace it through the frozen M1 MCP boundary."],
  "/dashboard": ["Dashboard", "A calm overview of your memory layer.", "Start by connecting an authenticated Cloud adapter. Your dashboard will appear here once the server-side session is verified."],
  "/memories": ["Memories", "Review what your agents remember.", "No memories are loaded in this preview. The administrative adapter will provide paginated, tenant-scoped results without browser database access."],
  "/connections": ["Connections", "Choose which clients can use your memory.", "Connection scopes and revocation are server operations. Nothing is connected in this preview."],
  "/consent": ["Connection consent", "Review access before it begins.", "The server supplies the client, purpose, scopes, and consent version. The browser can only approve or deny that request."],
  "/agents": ["Agents", "Issue narrow credentials for your own agents.", "Agent credentials are one-time displayed, hashed at rest, scoped, and revocable. Provisioning is waiting for the Cloud adapter."],
  "/settings/security": ["Security settings", "Sessions, consent, and account controls.", "A verified server session is required before security settings or destructive actions can be enabled."],
  "/docs": ["Documentation", "Connect the surfaces you actually use.", "Read the public onboarding contract and surface-specific recipes. Each compatibility row stays conservative until lifecycle evidence exists."],
  "/status": ["System status", "A transparent view of what is available.", "The Community core is available locally. Cloud identity, remote MCP, and hosted administrative APIs are not provisioned in this preview."],
};

function renderCompatibility() {
  const target = document.querySelector("#compatibility-table");
  if (!target) return;
  target.innerHTML = `<table><thead><tr><th>Surface</th><th>Planned transport</th><th>Status</th></tr></thead><tbody>${surfaces.map(([name, transport, state]) => `<tr><td>${name}</td><td>${transport}</td><td><span class="status status--${state.toLowerCase().replaceAll(" ", "-")}">${state}</span></td></tr>`).join("")}</tbody></table>`;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[character]);
}

function renderRoutePage(path, content) {
  document.body.classList.remove("account-mode");
  const page = routePages[path];
  if (!page) return false;
  const [title, lede] = page;
  document.querySelector("#main").innerHTML = `<section class="section route-page"><p class="eyebrow">UMCP / ${path.slice(1)}</p><h1>${title}</h1><p class="lede">${lede}</p>${content}</section>`;
  document.title = `${title} — UMCP`;
  return true;
}

function memoryStateLabel(state) {
  return ({ candidate: "Needs review", confirmed: "Confirmed", pinned: "Pinned", stale: "Review", active: "Active", archived: "Archived", contradicted: "Conflict", superseded: "Superseded" })[state] || state || "Memory";
}

function memoryCard(memory) {
  const space = memory.space || "General";
  const type = memory.type || memory.memory_type || "memory";
  return `<article class="vault-memory-card"><div class="vault-memory-card__meta"><span class="memory-type">${escapeHtml(type)}</span><span class="memory-state memory-state--${escapeHtml(memory.state || "active")}">${escapeHtml(memoryStateLabel(memory.state))}</span></div><a href="#/memories/${encodeURIComponent(memory.id)}">${escapeHtml(memory.content)}</a><footer><span>${escapeHtml(space)}</span><span>v${escapeHtml(memory.version || 1)}</span></footer></article>`;
}

function renderAccountPage({ path, title, lede, session, content, toolbar = "", query = "" }) {
  document.body.classList.add("account-mode");
  document.querySelector("#main").innerHTML = renderAccountShell({ path, title, lede, session, content, toolbar });
  document.title = `${title} — UMCP`;
  const search = document.querySelector(".vault-search");
  const input = search?.querySelector("input");
  if (input) input.value = query;
  search?.addEventListener("submit", (event) => {
    event.preventDefault();
    const value = new FormData(search).get("query")?.toString().trim() || "";
    location.hash = value ? `#/memories?query=${encodeURIComponent(value)}` : "#/memories";
  });
  document.removeEventListener("keydown", focusVaultSearch);
  document.addEventListener("keydown", focusVaultSearch);
  document.querySelector("[data-account-logout]")?.addEventListener("click", () => { void accountLogout(); });
  return true;
}

function focusVaultSearch(event) {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
    event.preventDefault();
    document.querySelector("#vault-search-input")?.focus();
  }
}

async function accountLogout() {
  const adapter = getAdminAdapter();
  try {
    await adapter.logout();
    location.hash = "#login";
    location.reload();
  } catch {
    globalThis.alert("We could not log out. Please try again.");
  }
}

function unavailableRoute(path, message) {
  return renderRoutePage(path, `<div class="empty-state"><span class="mono">SERVER ADAPTER REQUIRED</span><p>${message}</p><a class="button button--dark" href="#top">Back to overview</a></div>`);
}

function memoryItems(result) {
  return Array.isArray(result.memories) ? result.memories.map((item) => item.memory || item) : [];
}

function idempotencyKey() {
  return globalThis.crypto?.randomUUID?.() || `web-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

async function renderAuthenticatedRoute(path, { query = "" } = {}) {
  const adapter = getAdminAdapter();
  const staticPage = routePages[path];
  if (!staticPage) return false;
  if (adapter.status !== "ready") return unavailableRoute(path, staticPage[2]);
  renderRoutePage(path, `<div class="empty-state"><span class="mono">LOADING SECURE DATA</span><p>Checking the server-side session…</p></div>`);
  try {
    const session = await adapter.session();
    if (path === "/dashboard") {
      const [memoryResult, connectionResult] = await Promise.allSettled([adapter.listMemories(), adapter.listConnections()]);
      const result = memoryResult.status === "fulfilled" ? memoryResult.value : { memories: [] };
      const connections = connectionResult.status === "fulfilled" ? connectionResult.value.connections || [] : [];
      const items = memoryItems(result);
      const count = Number(result.count || memoryItems(result).length);
      const pending = items.filter((memory) => ["candidate", "stale", "contradicted"].includes(memory.state)).length;
      const pinned = items.filter((memory) => memory.state === "pinned").length;
      const activeConnections = connections.filter((connection) => connection.status === "active").length;
      const recent = items.slice(0, 4);
      const content = `<section class="vault-stats" aria-label="Vault overview"><a href="#/memories"><strong>${count}</strong><span>Memories</span><small>Your searchable vault</small></a><a href="#/inbox"><strong>${pending}</strong><span>To review</span><small>Candidates and conflicts</small></a><a href="#/connections"><strong>${activeConnections}</strong><span>Connections</span><small>Authorized clients</small></a></section>
        <div class="vault-dashboard-grid"><section class="vault-panel"><header><div><p class="account-eyebrow">Continue exploring</p><h2>Recent memories</h2></div><a href="#/memories">View all</a></header><div class="vault-memory-list">${recent.length ? recent.map(memoryCard).join("") : '<div class="vault-empty"><span>✦</span><h3>Your vault is ready.</h3><p>Memories captured by an authorized connection will appear here.</p></div>'}</div></section>
        <aside class="vault-panel mental-notes"><header><div><p class="account-eyebrow">Keep close</p><h2>Mental notes</h2></div><span>${pinned}</span></header>${pinned ? `<div class="vault-memory-list">${items.filter((memory) => memory.state === "pinned").slice(0, 3).map(memoryCard).join("")}</div>` : '<div class="vault-empty vault-empty--compact"><span>◇</span><h3>Nothing pinned yet</h3><p>Pin an important memory to keep it within reach.</p></div>'}</aside></div>`;
      return renderAccountPage({ path, title: "Today", lede: "A calm overview of what your assistants remember.", session, content });
    }
    if (path === "/memories") {
      const result = await adapter.listMemories(query);
      const items = memoryItems(result);
      const spaces = [...new Set(items.map((memory) => memory.space).filter(Boolean))];
      const toolbar = `<div class="account-page-actions"><button class="icon-button is-active" type="button" aria-label="Card view">▦</button><button class="icon-button" type="button" aria-label="List view" disabled>☷</button><button class="button button--dark" type="button" disabled title="Memory creation will be enabled with the next API contract">New memory</button></div>`;
      const filters = `<div class="vault-filterbar"><span>${items.length} ${items.length === 1 ? "memory" : "memories"}</span><button type="button" class="filter-chip is-active">All</button>${spaces.slice(0, 4).map((space) => `<button type="button" class="filter-chip">${escapeHtml(space)}</button>`).join("")}<button type="button" class="filter-chip">Filters <span aria-hidden="true">＋</span></button></div>`;
      const content = `${filters}<section class="vault-memory-grid">${items.length ? items.map(memoryCard).join("") : `<div class="vault-empty vault-empty--wide"><span>⌕</span><h2>${query ? "No matching memories" : "Your memory vault is empty"}</h2><p>${query ? `Try a different phrase or clear “${escapeHtml(query)}”.` : "Once an authorized assistant captures a memory, it will appear here with its origin and lifecycle."}</p>${query ? '<a class="button button--dark" href="#/memories">Clear search</a>' : ""}</div>`}</section>`;
      return renderAccountPage({ path, title: "Memories", lede: "Explore, understand, and control what stays with you.", session, content, toolbar, query });
    }
    if (path === "/connections") {
      const result = await adapter.listConnections();
      const rows = (result.connections || []).map((connection) => `<li>${escapeHtml(connection.name)} <small>${escapeHtml(connection.status)} · ${escapeHtml((connection.scopes || []).join(", "))} · last used: ${escapeHtml(connection.last_used_at || "Not used yet")}</small>${connection.status === "active" ? `<button type="button" data-revoke-connection="${escapeHtml(connection.id)}">Revoke</button>` : ""}</li>`).join("") || "<li>No connections have been created.</li>";
      renderAccountPage({ path, title: "Connections", lede: "Choose which assistants and clients can use your vault.", session, content: `<div class="account-control-card"><p class="mono">AUTHORIZED CLIENTS</p><ul class="data-list">${rows}</ul><form id="connection-form"><label for="connection-name">Connection name</label><input id="connection-name" name="name" required maxlength="128"><fieldset><legend>Scopes</legend>${scopeFields()}</fieldset><button class="button" type="submit">Create connection</button><p id="connection-action-status" role="status"></p></form></div>` });
      wireConnectionActions(adapter);
      return true;
    }
    if (path === "/agents") {
      const result = await adapter.listAgentCredentials();
      const rows = (result.credentials || []).map((credential) => `<li>${escapeHtml(credential.name)} <small>${escapeHtml(credential.revoked ? "revoked" : "active")} · ${escapeHtml((credential.scopes || []).join(", "))}</small>${!credential.revoked ? `<button type="button" data-revoke-agent="${escapeHtml(credential.id)}">Revoke</button>` : ""}</li>`).join("") || "<li>No agent credentials have been issued.</li>";
      renderAccountPage({ path, title: "Agents", lede: "Issue narrow, revocable access for your own agents.", session, content: `<div class="account-control-card"><p class="mono">AGENT CREDENTIALS</p><ul class="data-list">${rows}</ul><form id="agent-form"><label for="agent-name">Agent name</label><input id="agent-name" name="name" required maxlength="128"><label for="agent-expiry">Expiry (seconds)</label><input id="agent-expiry" name="expires_in_seconds" type="number" min="60" max="86400" value="3600" required><fieldset><legend>Scopes</legend>${scopeFields()}</fieldset><button class="button" type="submit">Issue credential</button><p id="agent-action-status" role="status"></p></form></div>` });
      wireAgentActions(adapter);
      return true;
    }
    if (path === "/settings/security") {
      renderAccountPage({ path, title: "Account & security", lede: "Manage your session, data, and account lifecycle.", session, content: `<div class="account-control-card"><p class="mono">VERIFIED SESSION</p><dl><div><dt>Account ID</dt><dd>${escapeHtml(session.subject_id)}</dd></div><div><dt>Vault ID</dt><dd>${escapeHtml(session.tenant_id)}</dd></div><div><dt>Scopes</dt><dd>${escapeHtml((session.scopes || []).join(", "))}</dd></div></dl><div class="card-actions"><button class="button" id="request-export" type="button">Request export</button><button class="button button--dark" id="request-deletion" type="button">Request account deletion</button><button id="logout" type="button">Log out</button></div><p id="security-action-status" role="status"></p></div>` });
      wireSecurityActions(adapter);
      return true;
    }
    if (path === "/status") {
      const capabilities = await adapter.capabilities();
      return renderAccountPage({ path, title: "System status", lede: "Current capabilities for this deployment.", session, content: `<div class="account-control-card"><p class="mono">${escapeHtml(capabilities.version)}</p><dl><div><dt>Authentication</dt><dd>${escapeHtml(capabilities.auth)}</dd></div><div><dt>Email delivery</dt><dd>${escapeHtml(capabilities.email_delivery)}</dd></div><div><dt>Tenant export</dt><dd>${capabilities.tenant_export ? "available" : "unavailable"}</dd></div></dl></div>` });
    }
  } catch {
    return renderRoutePage(path, `<div class="empty-state"><span class="mono">SERVER ERROR</span><p>We could not load this account data. Please try again later.</p></div>`);
  }
  return unavailableRoute(path, staticPage[2]);
}

let authSnapshot = { state: "idle", message: "" };

function authStatus(message, state = "") {
  const target = document.querySelector("#login-status");
  if (!target) return;
  target.dataset.state = state;
  target.textContent = message;
}

function authErrorMessage(error) {
  switch (error?.code) {
    case "expired_callback": return "This sign-in link has expired. Request a new one and try again.";
    case "revoked": return "This connection was revoked. Sign in again to request access.";
    case "authentication_required": return "Your session is no longer available. Sign in again to continue.";
    case "invalid_callback": return "This callback is invalid or has already been used.";
    case "invalid_email": return "Enter a valid email address to request the local sign-in link.";
    case "consent_already_decided": return "This consent request is no longer available.";
    default: return "We could not complete that request. Please try again.";
  }
}

function scopeDescription(scope) {
  return {
    "memory:read": "Read memories when the client asks for context",
    "memory:write": "Create or update memories",
    "memory:delete": "Forget memories on your instruction",
    "memory:export": "Request a tenant export",
    "connections:manage": "Manage this connection",
  }[scope] || scope;
}

async function renderConsentRoute() {
  const adapter = getAuthAdapter();
  if (getAdminAdapter().status === "ready" && adapter.mode === "fixture") {
    return unavailableRoute("/consent", "The deployed server must inject its H04 consent adapter before this screen can be used.");
  }
  if (adapter.status !== "ready") return unavailableRoute("/consent", "A verified server session is required before consent can be reviewed.");
  renderRoutePage("/consent", `<div class="empty-state"><span class="mono">LOADING CONSENT</span><p>Checking the server-owned request…</p></div>`);
  try {
    const request = await adapter.consentRequest();
    const scopes = (request.scopes || []).map((scope) => `<li><strong>${escapeHtml(scope)}</strong><span>${escapeHtml(scopeDescription(scope))}</span></li>`).join("");
    renderRoutePage("/consent", `<div class="consent-card" data-state="${escapeHtml(authSnapshot.state || "ready")}"><p class="mono">CONSENT REQUEST / ${escapeHtml(request.policy_version)}</p><h2>${escapeHtml(request.client_name)} wants access.</h2><dl><div><dt>Purpose</dt><dd>${escapeHtml(request.purpose)}</dd></div><div><dt>Client</dt><dd>${escapeHtml(request.client_id)}</dd></div></dl><section class="scope-review" aria-labelledby="scope-review-heading"><p class="eyebrow" id="scope-review-heading">Requested scopes</p><ul>${scopes}</ul></section><p class="caption">The server records this decision as consent ${escapeHtml(request.request_id)}. You can revoke this connection later; the browser never chooses a tenant or expands these scopes.</p><div class="card-actions"><button class="button" id="grant-consent" type="button">Allow access</button><button class="button button--quiet" id="deny-consent" type="button">Deny</button></div><p id="consent-action-status" role="status" aria-live="polite"></p></div>`);
    wireConsentActions(adapter);
    return true;
  } catch (error) {
    const state = error?.code === "revoked" ? "revoked" : error?.code === "consent_already_decided" ? "denied" : "error";
    const message = authErrorMessage(error);
    authSnapshot = { state, message };
    return renderRoutePage("/consent", `<div class="empty-state" data-state="${state}"><span class="mono">${state === "revoked" ? "CONNECTION REVOKED" : state === "denied" ? "CONSENT CLOSED" : "CONSENT UNAVAILABLE"}</span><p>${escapeHtml(message)}</p><div class="card-actions"><a class="button" href="#login">Return to sign in</a><button class="button button--quiet" data-action="retry-consent" type="button">Retry</button></div></div>`);
  }
}

function wireConsentActions(adapter) {
  const status = document.querySelector("#consent-action-status");
  const grant = document.querySelector("#grant-consent");
  const deny = document.querySelector("#deny-consent");
  if (!status || !grant || !deny) return;
  const setBusy = (message) => {
    grant.disabled = true;
    deny.disabled = true;
    status.dataset.state = "loading";
    status.textContent = message;
  };
  grant.addEventListener("click", async () => {
    setBusy("Saving your consent decision…");
    try {
      await adapter.grantConsent();
      authSnapshot = { state: "granted", message: "" };
      location.hash = "#/connections";
    } catch (error) {
      grant.disabled = false;
      deny.disabled = false;
      status.dataset.state = error?.code === "revoked" ? "revoked" : "error";
      status.textContent = authErrorMessage(error);
    }
  });
  deny.addEventListener("click", async () => {
    setBusy("Recording that access was denied…");
    try {
      await adapter.denyConsent();
      authSnapshot = { state: "denied", message: "Access was denied. No connection was created." };
      location.hash = "#login";
      authStatus(authSnapshot.message, "denied");
    } catch (error) {
      grant.disabled = false;
      deny.disabled = false;
      status.dataset.state = "error";
      status.textContent = authErrorMessage(error);
    }
  });
  document.querySelector("[data-action='retry-consent']")?.addEventListener("click", () => { void renderConsentRoute(); });
}

async function renderConnectionsRoute() {
  const admin = getAdminAdapter();
  const adapter = admin.status === "ready" ? admin : getAuthAdapter();
  if (adapter.status !== "ready") return unavailableRoute("/connections", routePages["/connections"][2]);
  renderRoutePage("/connections", `<div class="empty-state"><span class="mono">LOADING CONNECTIONS</span><p>Checking server-owned access records…</p></div>`);
  try {
    const result = await adapter.listConnections();
    const rows = (result.connections || []).map((connection) => `<li><span><strong>${escapeHtml(connection.name || connection.client_id || "Unnamed connection")}</strong><small>${escapeHtml(connection.status)} · ${escapeHtml((connection.scopes || []).join(", "))}</small><small>Last used: ${escapeHtml(connection.last_used_at || "Not used yet")}</small></span>${connection.status === "active" ? `<button type="button" data-revoke-h05="${escapeHtml(connection.id)}">Revoke</button>` : ""}</li>`).join("") || "<li>No connections have been approved.</li>";
    renderRoutePage("/connections", `<div class="control-card"><p class="mono">SERVER-OWNED CONNECTIONS</p><p>Each client has its own scopes and revocation state. Last-used data is audit-safe metadata only.</p><ul class="connection-list">${rows}</ul><p id="connection-action-status" class="action-result" role="status" aria-live="polite"></p></div>`);
    document.querySelectorAll("[data-revoke-h05]").forEach((button) => button.addEventListener("click", async () => {
      if (!globalThis.confirm("Revoke this connection? Its access will stop.")) return;
      button.disabled = true;
      const status = document.querySelector("#connection-action-status");
      status.textContent = "Revoking connection…";
      try {
        await adapter.revokeConnection(button.dataset.revokeH05);
        authSnapshot = { state: "revoked", message: "Connection revoked. Its session is no longer usable." };
        await renderConnectionsRoute();
      } catch (error) {
        button.disabled = false;
        status.dataset.state = error?.code === "revoked" ? "revoked" : "error";
        status.textContent = authErrorMessage(error);
      }
    }));
    return true;
  } catch (error) {
    return renderRoutePage("/connections", `<div class="empty-state" data-state="${error?.code === "revoked" ? "revoked" : "error"}"><span class="mono">${error?.code === "revoked" ? "CONNECTION REVOKED" : "CONNECTIONS UNAVAILABLE"}</span><p>${escapeHtml(authErrorMessage(error))}</p><div class="card-actions"><a class="button" href="#login">Return to sign in</a><button class="button button--quiet" data-action="retry-connections" type="button">Retry</button></div></div>`);
  }
}

let inboxSnapshot = { restore: null, recall: null };

function inboxActionStatus(message, state = "") {
  const target = document.querySelector("#inbox-action-status");
  if (!target) return;
  target.dataset.state = state;
  target.textContent = message;
}

async function renderInboxRoute() {
  const adapter = getMemoryInboxAdapter();
  renderRoutePage("/inbox", renderMemoryInbox({ state: "loading", mode: adapter.status }));
  try {
    const [inbox, memories, connections] = await Promise.all([adapter.listInbox({ space: "MBA" }), adapter.listMemories(), adapter.listConnections()]);
    const content = renderMemoryInbox({
      state: "success",
      mode: adapter.status,
      candidates: inbox.candidates || [],
      memories: memories.memories || [],
      connections: connections.connections || [],
      recall: inboxSnapshot.recall,
      restore: inboxSnapshot.restore,
    });
    const admin = getAdminAdapter();
    if (admin.status === "ready") {
      const session = await admin.session();
      renderAccountPage({ path: "/inbox", title: "Inbox", lede: "Review what your assistants would like to remember.", session, content });
    } else {
      renderRoutePage("/inbox", content);
    }
    wireInboxActions(adapter);
    return true;
  } catch {
    const content = renderMemoryInbox({ state: "error", mode: adapter.status });
    const admin = getAdminAdapter();
    if (admin.status === "ready") {
      try {
        const session = await admin.session();
        renderAccountPage({ path: "/inbox", title: "Inbox", lede: "Review what your assistants would like to remember.", session, content });
      } catch { renderRoutePage("/inbox", content); }
    } else {
      renderRoutePage("/inbox", content);
    }
    wireInboxActions(adapter);
    return true;
  }
}

function inboxTarget(button) {
  return { id: button.dataset.memoryId, expected_version: Number(button.dataset.expectedVersion) };
}

function wireInboxActions(adapter) {
  document.querySelectorAll("[data-action='retry-inbox']").forEach((button) => button.addEventListener("click", () => { void renderInboxRoute(); }));
  document.querySelectorAll("[data-action='confirm']").forEach((button) => button.addEventListener("click", async () => {
    const target = inboxTarget(button);
    const edit = document.querySelector(`[data-memory-edit="${CSS.escape(target.id)}"]`);
    button.disabled = true;
    inboxActionStatus("Confirming candidate and creating version…", "loading");
    try {
      const patch = edit?.value ? { content: edit.value } : undefined;
      await adapter.confirmCandidate({ ...target, patch, idempotency_key: idempotencyKey() });
      inboxSnapshot = { ...inboxSnapshot, recall: null };
      await renderInboxRoute();
      inboxActionStatus("Candidate confirmed. It is now eligible for policy-filtered recall.", "success");
    } catch (error) { button.disabled = false; inboxActionStatus(`Confirmation failed: ${String(error.message || "safe application error")}.`, "error"); }
  }));
  document.querySelectorAll("[data-action='discard']").forEach((button) => button.addEventListener("click", async () => {
    if (!globalThis.confirm("Discard this candidate? Its content will be forgotten and cannot be restored.")) return;
    const target = inboxTarget(button);
    button.disabled = true;
    inboxActionStatus("Forgetting candidate…", "loading");
    try {
      await adapter.discardCandidate({ ...target, idempotency_key: idempotencyKey() });
      inboxSnapshot = { recall: null, restore: null };
      await renderInboxRoute();
      inboxActionStatus("Candidate forgotten. Restore/import is blocked by its tombstone.", "success");
    } catch (error) { button.disabled = false; inboxActionStatus(`Discard failed: ${String(error.message || "safe application error")}.`, "error"); }
  }));
  document.querySelectorAll("[data-action='pin'], [data-action='unpin']").forEach((button) => button.addEventListener("click", async () => {
    const target = inboxTarget(button);
    const pinned = button.dataset.action === "pin";
    button.disabled = true;
    inboxActionStatus(`${pinned ? "Pinning" : "Unpinning"} memory…`, "loading");
    try { await adapter.pinMemory({ ...target, pinned, idempotency_key: idempotencyKey() }); inboxSnapshot = { ...inboxSnapshot, recall: null }; await renderInboxRoute(); inboxActionStatus(`Memory ${pinned ? "pinned" : "unpinned"}.`, "success"); }
    catch (error) { button.disabled = false; inboxActionStatus(`Pin update failed: ${String(error.message || "safe application error")}.`, "error"); }
  }));
  document.querySelectorAll("[data-action='stale'], [data-action='review']").forEach((button) => button.addEventListener("click", async () => {
    const target = inboxTarget(button);
    const nextState = button.dataset.action === "stale" ? "stale" : "confirmed";
    button.disabled = true;
    inboxActionStatus(`${nextState === "stale" ? "Marking memory stale" : "Reviewing stale memory"}…`, "loading");
    try { await adapter.updateMemory({ ...target, state: nextState, idempotency_key: idempotencyKey() }); inboxSnapshot = { ...inboxSnapshot, recall: null }; await renderInboxRoute(); inboxActionStatus(`Memory is now ${nextState}.`, "success"); }
    catch (error) { button.disabled = false; inboxActionStatus(`Lifecycle update failed: ${String(error.message || "safe application error")}.`, "error"); }
  }));
  document.querySelectorAll("[data-action='forget']").forEach((button) => button.addEventListener("click", async () => {
    if (!globalThis.confirm("Forget this memory? This is terminal for the memory ID.")) return;
    const target = inboxTarget(button);
    button.disabled = true;
    inboxActionStatus("Forgetting memory…", "loading");
    try {
      await adapter.forgetMemory({ id: target.id, idempotency_key: idempotencyKey() });
      inboxSnapshot = { recall: null, restore: null };
      await renderInboxRoute();
      inboxActionStatus("Memory forgotten. Restore/import is blocked by its tombstone.", "success");
    } catch (error) { button.disabled = false; inboxActionStatus(`Forget failed: ${String(error.message || "safe application error")}.`, "error"); }
  }));
  document.querySelectorAll("[data-action='recall']").forEach((button) => button.addEventListener("click", async () => {
    button.disabled = true;
    inboxActionStatus("Running explicit Work → MBA recall…", "loading");
    try { inboxSnapshot = { ...inboxSnapshot, recall: await adapter.recall({ query: "incentives outcome", context_space: "Work", include_spaces: ["MBA"], limit: 10 }) }; await renderInboxRoute(); inboxActionStatus("Recall completed with a bounded reason, not a hidden reasoning trace.", "success"); }
    catch (error) { button.disabled = false; inboxActionStatus(`Recall failed: ${String(error.message || "safe application error")}.`, "error"); }
  }));
  document.querySelectorAll("[data-action='restore']").forEach((button) => button.addEventListener("click", async () => {
    button.disabled = true;
    inboxActionStatus("Attempting fixture restore/import…", "loading");
    try { inboxSnapshot = { ...inboxSnapshot, restore: await adapter.restoreMemory({ id: M1_FIXTURE_MEMORY_ID }) }; await renderInboxRoute(); inboxActionStatus("Restore result received; no forgotten content was recreated.", "success"); }
    catch (error) { button.disabled = false; inboxActionStatus(`Restore check failed: ${String(error.message || "safe application error")}.`, "error"); }
  }));
  document.querySelectorAll("[data-action='revoke']").forEach((button) => button.addEventListener("click", async () => {
    if (!globalThis.confirm("Revoke this connection? Its access will stop without revoking other clients.")) return;
    button.disabled = true;
    inboxActionStatus("Revoking connection…", "loading");
    try { await adapter.revokeConnection(button.dataset.connectionId); await renderInboxRoute(); inboxActionStatus("Connection revoked independently.", "success"); }
    catch (error) { button.disabled = false; inboxActionStatus(`Revoke failed: ${String(error.message || "safe application error")}.`, "error"); }
  }));
}

function scopeFields() {
  return ["memory:read", "memory:write", "memory:delete", "memory:export", "connections:manage"]
    .map((scope) => `<label><input type="checkbox" name="scope" value="${scope}" ${scope === "memory:read" ? "checked" : ""}> ${scope}</label>`)
    .join("");
}

function selectedScopes(form) {
  return new FormData(form).getAll("scope").map(String);
}

function wireConnectionActions(adapter) {
  const form = document.querySelector("#connection-form");
  const status = document.querySelector("#connection-action-status");
  if (!form || !status) return;
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const scopes = selectedScopes(form);
    if (!scopes.length || !form.reportValidity()) return;
    status.textContent = "Creating connection…";
    try {
      await adapter.createConnection({ name: new FormData(form).get("name"), scopes });
      await renderAuthenticatedRoute("/connections");
    } catch { status.textContent = "We could not create this connection. Please try again."; }
  });
  document.querySelectorAll("[data-revoke-connection]").forEach((button) => button.addEventListener("click", async () => {
    if (!globalThis.confirm("Revoke this connection? Its access will stop.")) return;
    try { await adapter.revokeConnection(button.dataset.revokeConnection); await renderAuthenticatedRoute("/connections"); }
    catch { status.textContent = "We could not revoke this connection. Please try again."; }
  }));
}

function wireAgentActions(adapter) {
  const form = document.querySelector("#agent-form");
  const status = document.querySelector("#agent-action-status");
  if (!form || !status) return;
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const scopes = selectedScopes(form);
    if (!scopes.length || !form.reportValidity()) return;
    status.textContent = "Issuing credential…";
    try {
      const result = await adapter.createAgentCredential({ name: new FormData(form).get("name"), scopes, expires_in_seconds: Number(new FormData(form).get("expires_in_seconds")) });
      status.textContent = `Copy this credential now; it will not be shown again: ${result.token}`;
    } catch { status.textContent = "We could not issue a credential. Please try again."; }
  });
  document.querySelectorAll("[data-revoke-agent]").forEach((button) => button.addEventListener("click", async () => {
    if (!globalThis.confirm("Revoke this credential? The agent will lose access.")) return;
    try { await adapter.revokeAgentCredential(button.dataset.revokeAgent); await renderAuthenticatedRoute("/agents"); }
    catch { status.textContent = "We could not revoke this credential. Please try again."; }
  }));
}

function wireSecurityActions(adapter) {
  const status = document.querySelector("#security-action-status");
  const exportButton = document.querySelector("#request-export");
  const deletionButton = document.querySelector("#request-deletion");
  const logoutButton = document.querySelector("#logout");
  if (!status || !exportButton || !deletionButton || !logoutButton) return;
  exportButton.addEventListener("click", async () => {
    status.textContent = "Requesting export…";
    try {
      const result = await adapter.exportTenant();
      status.textContent = `Export request ${result.receipt.id} is ${result.receipt.status}.`;
    } catch {
      status.textContent = "We could not request an export. Please try again.";
    }
  });
  deletionButton.addEventListener("click", async () => {
    if (!globalThis.confirm("Request account deletion? This starts a destructive server-side workflow.")) return;
    status.textContent = "Requesting account deletion…";
    try {
      const result = await adapter.requestAccountDeletion();
      status.textContent = `Deletion request ${result.receipt.id} is ${result.receipt.status}.`;
    } catch {
      status.textContent = "We could not request account deletion. Please try again.";
    }
  });
  logoutButton.addEventListener("click", async () => {
    try {
      await adapter.logout();
      location.hash = "#login";
      location.reload();
    } catch {
      status.textContent = "We could not log out. Please try again.";
    }
  });
}

async function renderMemoryDetail(memoryId) {
  const adapter = getAdminAdapter();
  if (adapter.status !== "ready") return unavailableRoute("/memories", "A verified server session is required to view a memory.");
  renderRoutePage("/memories", `<div class="empty-state"><span class="mono">LOADING MEMORY</span></div>`);
  try {
    const [memory, session] = await Promise.all([adapter.getMemory(memoryId), adapter.session()]);
    const metadata = `<aside class="memory-inspector"><p class="account-eyebrow">About this memory</p><dl><div><dt>Type</dt><dd>${escapeHtml(memory.type || memory.memory_type || "memory")}</dd></div><div><dt>State</dt><dd>${escapeHtml(memoryStateLabel(memory.state))}</dd></div><div><dt>Space</dt><dd>${escapeHtml(memory.space || "General")}</dd></div><div><dt>Version</dt><dd>${escapeHtml(memory.version)}</dd></div></dl><p class="caption">Origin and relation details appear here when supplied by the administrative API.</p></aside>`;
    const editor = `<section class="memory-editor"><a class="back-link" href="#/memories">← All memories</a><div class="memory-editor__content"><span class="memory-type">${escapeHtml(memory.type || memory.memory_type || "memory")}</span><p>${escapeHtml(memory.content)}</p></div><form id="memory-edit-form"><label for="memory-content">Edit memory</label><textarea id="memory-content" name="content" required>${escapeHtml(memory.content)}</textarea><div class="card-actions"><button class="button" type="submit">Save new version</button><button class="button button--quiet" id="forget-memory" type="button">Forget memory</button></div><p id="memory-action-status" role="status"></p></form></section>`;
    renderAccountPage({ path: `/memories/${memoryId}`, title: "Memory detail", lede: "Inspect its meaning, lifecycle, and origin.", session, content: `<div class="memory-detail-layout">${editor}${metadata}</div>` });
    wireMemoryActions(adapter, memory);
    return true;
  } catch {
    return renderRoutePage("/memories", `<div class="empty-state"><span class="mono">NOT AVAILABLE</span><p>This memory is no longer available in the current session.</p><a class="button button--dark" href="#/memories">Back to memories</a></div>`);
  }
}

function wireMemoryActions(adapter, memory) {
  const form = document.querySelector("#memory-edit-form");
  const forget = document.querySelector("#forget-memory");
  const status = document.querySelector("#memory-action-status");
  if (!form || !forget || !status) return;
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    status.textContent = "Saving a new version…";
    try {
      await adapter.updateMemory(memory.id, {
        expected_version: memory.version,
        patch: { content: new FormData(form).get("content") },
        idempotency_key: idempotencyKey(),
      });
      status.textContent = "Saved. Refreshing the verified version…";
      await renderMemoryDetail(memory.id);
    } catch {
      status.textContent = "We could not save this version. It may have changed; refresh and try again.";
    }
  });
  forget.addEventListener("click", async () => {
    if (!globalThis.confirm("Forget this memory? This cannot be undone from this screen.")) return;
    status.textContent = "Forgetting memory…";
    try {
      await adapter.forgetMemory(memory.id, idempotencyKey());
      location.hash = "#/memories";
    } catch {
      status.textContent = "We could not forget this memory. Please try again.";
    }
  });
}

function restoreLanding() {
  if (!location.hash || location.hash === "#top" || location.hash === "#login" || location.hash === "#how" || location.hash === "#control" || location.hash === "#compatibility" || location.hash === "#security") {
    document.body.classList.remove("account-mode");
    if (document.querySelector(".route-page")) location.reload();
    document.title = "UMCP — Open Memory Protocol";
  }
}

function wireLogin() {
  const form = document.querySelector("#login-form");
  const status = document.querySelector("#login-status");
  const google = document.querySelector("#google-login");
  const adapter = getAuthAdapter();
  const admin = getAdminAdapter();
  if (!form || !status || !google) return;
  const hostedGoogle = globalThis.__UMCP_GOOGLE_LOGIN_URL__;
  if (typeof hostedGoogle === "string" && /^\/(?![\\/])/.test(hostedGoogle)) {
    form.hidden = true;
    document.querySelector(".or-divider")?.setAttribute("hidden", "");
    status.textContent = "Redirecting to secure Google sign-in…";
    google.addEventListener("click", () => { location.assign(hostedGoogle); });
    return;
  }

  const start = async (method, email) => {
    if (method === "google" && admin.status === "ready" && adapter.mode === "fixture") {
      authStatus("Google is not configured for this deployment. CP-2 must approve an IdP before this option is enabled.", "unavailable");
      return;
    }
    if (adapter.status !== "ready") {
      authStatus("Sign-in is not connected here. A deployed server must provide the verified identity flow.", "unavailable");
      return;
    }
    google.disabled = true;
    form.querySelector("button[type='submit']").disabled = true;
    authStatus(method === "google" ? "Preparing the local callback…" : "Requesting a local sign-in link…", "loading");
    try {
      if (method === "magic_link" && admin.status === "ready" && adapter.mode === "fixture") {
        await admin.requestMagicLink({ email });
        authStatus("If this address can receive sign-in mail, a link will arrive shortly.", "success");
        return;
      }
      const result = await adapter.beginLogin({ method, email });
      if (method === "google") {
        location.hash = result.callback_hash;
        return;
      }
      authStatus("The local fixture accepted the request. No email was sent.", "success");
      const link = document.querySelector("#open-magic-link");
      if (link) link.remove();
      const action = document.createElement("button");
      action.id = "open-magic-link";
      action.type = "button";
      action.className = "button button--dark";
      action.textContent = "Open local sign-in link";
      action.addEventListener("click", () => { location.hash = adapter.openCapturedLink(); });
      status.insertAdjacentElement("afterend", action);
    } catch (error) {
      authStatus(authErrorMessage(error), error?.code === "expired_callback" ? "expired" : "error");
    } finally {
      google.disabled = false;
      form.querySelector("button[type='submit']").disabled = false;
    }
  };

  google.addEventListener("click", () => { void start("google"); });
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    await start("magic_link", new FormData(form).get("email"));
  });
}

async function route() {
  const hashParts = location.hash.match(/^#\/callback\?(.+)$/);
  const query = hashParts ? new URLSearchParams(hashParts[1]) : new URLSearchParams(location.search);
  const callbackToken = query.get("token");
  const callbackCode = query.get("code");
  if (callbackToken || callbackCode) {
    const adapter = callbackCode ? getAuthAdapter() : getAdminAdapter();
    try {
      if (callbackCode) {
        await adapter.completeCallback({ code: callbackCode, state: query.get("state") });
        authSnapshot = { state: "authenticated", message: "" };
        location.hash = "#/consent";
      } else {
        await adapter.completeMagicLink(callbackToken);
        history.replaceState({}, "", `${location.pathname}${location.hash || "#/dashboard"}`);
        if (!location.hash) location.hash = "#/dashboard";
      }
    } catch (error) {
      if (callbackCode) {
        authSnapshot = { state: error?.code === "expired_callback" ? "expired" : "error", message: authErrorMessage(error) };
        location.hash = "#login";
      } else {
        history.replaceState({}, "", `${location.pathname}${location.hash || "#login"}`);
      }
      const loginStatus = document.querySelector("#login-status");
      if (loginStatus) {
        loginStatus.dataset.state = authSnapshot.state || "error";
        loginStatus.textContent = callbackCode ? authSnapshot.message : "This sign-in link is invalid, expired, or has already been used.";
      }
    }
  }
  const rawPath = location.hash.startsWith("#/") ? location.hash.slice(1) : "";
  const [path, hashQuery = ""] = rawPath.split("?");
  const routeQuery = new URLSearchParams(hashQuery);
  if (path === "/consent") return renderConsentRoute();
  if (path === "/connections" && getAdminAdapter().status !== "ready") return renderConnectionsRoute();
  if (path === "/inbox") return renderInboxRoute();
  const detail = path.match(/^\/memories\/([^/]+)$/);
  if (detail) return renderMemoryDetail(decodeURIComponent(detail[1]));
  if (path && await renderAuthenticatedRoute(path, { query: routeQuery.get("query") || "" })) return;
  restoreLanding();
  renderCompatibility();
  wireLogin();
}

window.addEventListener("hashchange", () => { void route(); });
void route();
