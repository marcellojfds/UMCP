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

function renderRoute(path) {
  const page = routePages[path];
  if (!page) return false;
  const [title, lede, message] = page;
  document.querySelector("#main").innerHTML = `<section class="section route-page"><p class="eyebrow">UMCP / ${path.slice(1)}</p><h1>${title}</h1><p class="lede">${lede}</p><div class="empty-state"><span class="mono">SERVER ADAPTER REQUIRED</span><p>${message}</p><a class="button button--dark" href="#top">Back to overview</a></div></section>`;
  document.title = `${title} — UMCP`;
  return true;
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

function route() {
  const path = location.hash.startsWith("#/") ? location.hash.slice(1) : "";
  if (path && renderRoute(path)) return;
  restoreLanding();
  renderCompatibility();
  wireLogin();
}

window.addEventListener("hashchange", route);
route();
