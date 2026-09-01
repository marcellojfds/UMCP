/**
 * Browser boundary for the separately versioned administrative API (ADR 0010).
 * A trusted server injects this adapter after session verification. It must
 * derive principal and tenant from the session; no method accepts owner_id.
 */
import { accountPreviewEnabled, createAccountPreviewAdapter } from "./account-preview.js";

const previewAdapters = new WeakMap();

export const unavailableAdapter = Object.freeze({
  status: "unavailable",
  features: Object.freeze({ memoryWrite: false, memoryDelete: false, connections: false, agents: false, accountOperations: false }),
  async listMemories() { throw new Error("The authenticated administrative API is not available."); },
  async requestMagicLink() { throw new Error("The server-side email flow is not available."); },
  async exportTenant() { throw new Error("The authenticated administrative API is not available."); },
  async requestAccountDeletion() { throw new Error("The authenticated administrative API is not available."); },
  async revokeConnection() { throw new Error("The authenticated administrative API is not available."); },
});

export function getAdminAdapter(scope = globalThis) {
  const adapter = scope.__UMCP_ADMIN_ADAPTER__;
  if (adapter && adapter.status === "ready") return adapter;
  if (accountPreviewEnabled(scope)) {
    if (!previewAdapters.has(scope)) previewAdapters.set(scope, createAccountPreviewAdapter());
    return previewAdapters.get(scope);
  }

  // A deployment may opt in to an Admin API mounted on the current origin.
  // Reject protocol-relative URLs so a bootstrap value can never redirect
  // credentialed browser requests to another host.
  const baseUrl = scope.__UMCP_ADMIN_API_BASE_URL__;
  return typeof baseUrl === "string" && /^\/(?![\\/])/.test(baseUrl)
    ? createHttpAdminAdapter({ baseUrl })
    : unavailableAdapter;
}

/** Create the browser-side transport to the server-owned Admin API. */
export function createHttpAdminAdapter({ baseUrl = "", fetchImpl = fetch } = {}) {
  let csrf = null;
  let cachedSession = null;
  let cachedSessionTime = 0;
  const SESSION_TTL = 60000;
  const portalReadOnly = baseUrl === "/portal" || baseUrl.endsWith("/portal");
  async function request(path, options = {}) {
    const send = () => fetchImpl(`${baseUrl}${path}`, {
      credentials: "same-origin",
      headers: { "content-type": "application/json", ...(csrf ? { "x-umcp-csrf": csrf } : {}), ...(options.headers || {}) },
      ...options,
    });
    let response = await send();
    if (portalReadOnly && response.status === 401 && path !== "/api/refresh") {
      const refreshed = await fetchImpl(`${baseUrl}/api/refresh`, {
        method: "POST",
        credentials: "same-origin",
        headers: { "content-type": "application/json" },
      });
      if (refreshed.ok) response = await send();
    }
    if (!response.ok) {
      if (response.status === 401) {
        cachedSession = null;
        cachedSessionTime = 0;
      }
      const payload = await response.json().catch(() => ({}));
      const error = new Error("Administrative request failed");
      error.code = payload.error || (response.status === 401 ? "authentication_required" : "administrative_request_failed");
      error.status = response.status;
      throw error;
    }
    return response.status === 204 ? null : response.json();
  }
  return Object.freeze({
    status: "ready",
    features: Object.freeze({ memoryWrite: !portalReadOnly, memoryDelete: !portalReadOnly, connections: !portalReadOnly, agents: !portalReadOnly, accountOperations: !portalReadOnly }),
    requestMagicLink: ({ email }) => request("/api/auth/magic-link", { method: "POST", body: JSON.stringify({ email }) }),
    completeMagicLink: async (token) => { const result = await request(`/api/auth/callback?token=${encodeURIComponent(token)}`, { method: "GET" }); csrf = result.csrf; cachedSession = null; return result; },
    session: async () => {
      const now = Date.now();
      if (cachedSession && now - cachedSessionTime < SESSION_TTL) return cachedSession;
      const data = await request("/api/session", { method: "GET" });
      cachedSession = data;
      cachedSessionTime = Date.now();
      return data;
    },
    capabilities: () => request("/api/capabilities", { method: "GET" }),
    listMemories: (query = "") => request(`/api/memories?query=${encodeURIComponent(query)}`, { method: "GET" }),
    getMemory: (id) => request(`/api/memories/${encodeURIComponent(id)}`, { method: "GET" }),
    createMemory: (memory) => request("/api/memories", { method: "POST", body: JSON.stringify(memory) }),
    updateMemory: (id, update) => request(`/api/memories/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify(update) }),
    forgetMemory: (id, idempotencyKey) => request(`/api/memories/${encodeURIComponent(id)}?idempotency_key=${encodeURIComponent(idempotencyKey)}`, { method: "DELETE" }),
    listConnections: () => request("/api/connections", { method: "GET" }),
    createConnection: (connection) => request("/api/connections", { method: "POST", body: JSON.stringify(connection) }),
    revokeConnection: (id) => request(`/api/connections/${encodeURIComponent(id)}/revoke`, { method: "POST" }),
    createAgentCredential: (credential) => request("/api/agent-credentials", { method: "POST", body: JSON.stringify(credential) }),
    listAgentCredentials: () => request("/api/agent-credentials", { method: "GET" }),
    revokeAgentCredential: (id) => request(`/api/agent-credentials/${encodeURIComponent(id)}/revoke`, { method: "POST" }),
    exportTenant: () => request("/api/exports", { method: "POST" }),
    requestAccountDeletion: () => request("/api/account-deletions", { method: "POST" }),
    operationStatus: (id) => request(`/api/operations/${encodeURIComponent(id)}`, { method: "GET" }),
    logout: async () => {
      cachedSession = null;
      cachedSessionTime = 0;
      return request("/api/logout", { method: "POST" });
    },
  });
}
