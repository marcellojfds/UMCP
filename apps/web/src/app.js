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

document.querySelector("#compatibility-table").innerHTML = `<table><thead><tr><th>Surface</th><th>Planned transport</th><th>Status</th></tr></thead><tbody>${surfaces.map(([name, transport, status]) => `<tr><td>${name}</td><td>${transport}</td><td><span class="status status--${status.toLowerCase()}">${status}</span></td></tr>`).join("")}</tbody></table>`;

const form = document.querySelector("#login-form");
const status = document.querySelector("#login-status");
form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!form.reportValidity()) return;
  const adapter = getAdminAdapter();
  if (adapter.status !== "ready") {
    status.textContent = "Sign-in is not connected here. A deployed server must provide the verified email flow.";
    return;
  }
  status.textContent = "Requesting a sign-in link…";
  try {
    await adapter.requestMagicLink({ email: new FormData(form).get("email") });
    status.textContent = "If this address can receive sign-in mail, a link will arrive shortly.";
  } catch {
    status.textContent = "We could not process that request. Please try again later.";
  }
});
