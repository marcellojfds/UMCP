import { getAdminAdapter } from "./admin-adapter.js";

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
  "/dashboard": ["Dashboard", "A calm overview of your memory layer.", "Start by connecting an authenticated Cloud adapter. Your dashboard will appear here once the server-side session is verified."],
  "/memories": ["Memories", "Review what your agents remember.", "No memories are loaded in this preview. The administrative adapter will provide paginated, tenant-scoped results without browser database access."],
  "/connections": ["Connections", "Choose which clients can use your memory.", "Connection scopes and revocation are server operations. Nothing is connected in this preview."],
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
  const page = routePages[path];
  if (!page) return false;
  const [title, lede] = page;
  document.querySelector("#main").innerHTML = `<section class="section route-page"><p class="eyebrow">UMCP / ${path.slice(1)}</p><h1>${title}</h1><p class="lede">${lede}</p>${content}</section>`;
  document.title = `${title} — UMCP`;
  return true;
}

function unavailableRoute(path, message) {
  return renderRoutePage(path, `<div class="empty-state"><span class="mono">SERVER ADAPTER REQUIRED</span><p>${message}</p><a class="button button--dark" href="#top">Back to overview</a></div>`);
}

function memoryItems(result) {
  return Array.isArray(result.memories) ? result.memories.map((item) => item.memory || item) : [];
}

async function renderAuthenticatedRoute(path) {
  const adapter = getAdminAdapter();
  const staticPage = routePages[path];
  if (!staticPage) return false;
  if (adapter.status !== "ready") return unavailableRoute(path, staticPage[2]);
  renderRoutePage(path, `<div class="empty-state"><span class="mono">LOADING SECURE DATA</span><p>Checking the server-side session…</p></div>`);
  try {
    if (path === "/dashboard") {
      const [session, result] = await Promise.all([adapter.session(), adapter.listMemories()]);
      const count = Number(result.count || memoryItems(result).length);
      return renderRoutePage(path, `<div class="control-card"><p class="mono">SIGNED IN</p><p>${escapeHtml(session.subject_id)}</p><dl><div><dt>Tenant</dt><dd>${escapeHtml(session.tenant_id)}</dd></div><div><dt>Visible memories</dt><dd>${count}</dd></div></dl><a class="button button--dark" href="#/memories">Review memories</a></div>`);
    }
    if (path === "/memories") {
      const result = await adapter.listMemories();
      const items = memoryItems(result);
      const rows = items.length ? items.map((memory) => `<li><a href="#/memories/${encodeURIComponent(memory.id)}">${escapeHtml(memory.content)}</a><small>v${escapeHtml(memory.version)} · ${escapeHtml(memory.state)}</small></li>`).join("") : "<li>No memories match this account.</li>";
      return renderRoutePage(path, `<div class="control-card"><p class="mono">TENANT-SCOPED MEMORIES</p><ul class="data-list">${rows}</ul></div>`);
    }
    if (path === "/connections") {
      const result = await adapter.listConnections();
      const rows = (result.connections || []).map((connection) => `<li>${escapeHtml(connection.name)} <small>${escapeHtml(connection.status)} · ${escapeHtml((connection.scopes || []).join(", "))}</small></li>`).join("") || "<li>No connections have been created.</li>";
      return renderRoutePage(path, `<div class="control-card"><p class="mono">CONNECTIONS</p><ul class="data-list">${rows}</ul></div>`);
    }
    if (path === "/agents") {
      const result = await adapter.listAgentCredentials();
      const rows = (result.credentials || []).map((credential) => `<li>${escapeHtml(credential.name)} <small>${escapeHtml(credential.revoked ? "revoked" : "active")} · ${escapeHtml((credential.scopes || []).join(", "))}</small></li>`).join("") || "<li>No agent credentials have been issued.</li>";
      return renderRoutePage(path, `<div class="control-card"><p class="mono">AGENT CREDENTIALS</p><ul class="data-list">${rows}</ul></div>`);
    }
    if (path === "/status") {
      const capabilities = await adapter.capabilities();
      return renderRoutePage(path, `<div class="control-card"><p class="mono">${escapeHtml(capabilities.version)}</p><dl><div><dt>Authentication</dt><dd>${escapeHtml(capabilities.auth)}</dd></div><div><dt>Email delivery</dt><dd>${escapeHtml(capabilities.email_delivery)}</dd></div><div><dt>Tenant export</dt><dd>${capabilities.tenant_export ? "available" : "unavailable"}</dd></div></dl></div>`);
    }
  } catch {
    return renderRoutePage(path, `<div class="empty-state"><span class="mono">SERVER ERROR</span><p>We could not load this account data. Please try again later.</p></div>`);
  }
  return unavailableRoute(path, staticPage[2]);
}

async function renderMemoryDetail(memoryId) {
  const adapter = getAdminAdapter();
  if (adapter.status !== "ready") return unavailableRoute("/memories", "A verified server session is required to view a memory.");
  renderRoutePage("/memories", `<div class="empty-state"><span class="mono">LOADING MEMORY</span></div>`);
  try {
    const memory = await adapter.getMemory(memoryId);
    return renderRoutePage("/memories", `<div class="control-card"><p class="mono">MEMORY / v${escapeHtml(memory.version)}</p><p>${escapeHtml(memory.content)}</p><dl><div><dt>Type</dt><dd>${escapeHtml(memory.type)}</dd></div><div><dt>State</dt><dd>${escapeHtml(memory.state)}</dd></div></dl><a class="button button--dark" href="#/memories">Back to memories</a></div>`);
  } catch {
    return renderRoutePage("/memories", `<div class="empty-state"><span class="mono">NOT AVAILABLE</span><p>This memory is no longer available in the current session.</p><a class="button button--dark" href="#/memories">Back to memories</a></div>`);
  }
}

function restoreLanding() {
  if (!location.hash || location.hash === "#top" || location.hash === "#login" || location.hash === "#how" || location.hash === "#control" || location.hash === "#compatibility" || location.hash === "#security") {
    if (document.querySelector(".route-page")) location.reload();
    document.title = "UMCP — Open Memory Protocol";
  }
}

function wireLogin() {
  const form = document.querySelector("#login-form");
  const status = document.querySelector("#login-status");
  if (!form || !status) return;
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    const adapter = getAdminAdapter();
    if (adapter.status !== "ready") {
      status.dataset.state = "unavailable";
      status.textContent = "Sign-in is not connected here. A deployed server must provide the verified email flow.";
      return;
    }
    status.dataset.state = "loading";
    status.textContent = "Requesting a sign-in link…";
    try {
      await adapter.requestMagicLink({ email: new FormData(form).get("email") });
      status.dataset.state = "success";
      status.textContent = "If this address can receive sign-in mail, a link will arrive shortly.";
    } catch {
      status.dataset.state = "error";
      status.textContent = "We could not process that request. Please try again later.";
    }
  });
}

async function route() {
  const path = location.hash.startsWith("#/") ? location.hash.slice(1) : "";
  const detail = path.match(/^\/memories\/([^/]+)$/);
  if (detail) return renderMemoryDetail(decodeURIComponent(detail[1]));
  if (path && await renderAuthenticatedRoute(path)) return;
  restoreLanding();
  renderCompatibility();
  wireLogin();
}

window.addEventListener("hashchange", () => { void route(); });
void route();
