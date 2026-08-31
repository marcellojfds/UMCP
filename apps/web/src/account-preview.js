const previewMemories = Object.freeze([
  { id: "preview-1", content: "Prefer concise executive reports with a clear recommendation first.", type: "preference", state: "pinned", space: "Work", version: 3 },
  { id: "preview-2", content: "Poorly designed incentives make teams optimize the metric, not the outcome.", type: "lesson", state: "confirmed", space: "MBA", version: 1 },
  { id: "preview-3", content: "UMCP should make provenance visible whenever a memory is recalled.", type: "decision", state: "active", space: "UMCP", version: 2 },
  { id: "preview-4", content: "Explore a navigable personal Memory Atlas inspired by linked notes.", type: "goal", state: "candidate", space: "UMCP", version: 1 },
  { id: "preview-5", content: "Review the positioning hypothesis before the next product milestone.", type: "open_question", state: "stale", space: "Work", version: 2 },
]);

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

export function createAccountPreviewAdapter() {
  return Object.freeze({
    status: "ready",
    async session() {
      return { preview_mode: true, display_name: "Marcello Franco", email: "preview@umcp.local", subject_id: "preview-subject", tenant_id: "preview-vault", scopes: ["memory:read", "memory:write", "memory:delete"] };
    },
    async listMemories(query = "") {
      const normalized = String(query).trim().toLowerCase();
      const memories = normalized ? previewMemories.filter((memory) => `${memory.content} ${memory.space} ${memory.type}`.toLowerCase().includes(normalized)) : previewMemories;
      return { memories: clone(memories), count: memories.length };
    },
    async getMemory(id) {
      const memory = previewMemories.find((candidate) => candidate.id === id);
      if (!memory) throw new Error("not_found");
      return clone(memory);
    },
    async listConnections() {
      return { connections: [{ id: "preview-chatgpt", name: "ChatGPT", status: "active", scopes: ["memory:read", "memory:write"], last_used_at: "Today" }, { id: "preview-agent", name: "Personal agent", status: "active", scopes: ["memory:read"], last_used_at: "Yesterday" }] };
    },
    async listAgentCredentials() { return { credentials: [] }; },
    async capabilities() { return { version: "local-preview", auth: "fixture", email_delivery: "unavailable", tenant_export: false }; },
    async logout() {},
    async createConnection() { throw new Error("preview_read_only"); },
    async revokeConnection() { throw new Error("preview_read_only"); },
    async createAgentCredential() { throw new Error("preview_read_only"); },
    async revokeAgentCredential() { throw new Error("preview_read_only"); },
    async updateMemory() { throw new Error("preview_read_only"); },
    async forgetMemory() { throw new Error("preview_read_only"); },
    async exportTenant() { throw new Error("preview_read_only"); },
    async requestAccountDeletion() { throw new Error("preview_read_only"); },
  });
}

export function accountPreviewEnabled(scope = globalThis) {
  const hostname = scope.location?.hostname;
  const local = hostname === "localhost" || hostname === "127.0.0.1" || hostname === "[::1]";
  return local && new URLSearchParams(scope.location?.search || "").get("preview") === "account";
}
