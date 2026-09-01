const previewMemories = Object.freeze([
  { id: "preview-1", content: "Prefer concise executive reports for [[Leadership]] with a clear recommendation first. #work", type: "preference", state: "pinned", space: "Work", version: 3 },
  { id: "preview-2", content: "Poorly designed incentives make teams optimize the metric, not the outcome. [[Systems Thinking]] #mba", type: "lesson", state: "confirmed", space: "MBA", version: 1 },
  { id: "preview-3", content: "[[UMCP]] should make provenance visible whenever a memory is recalled across [[ChatGPT]] and [[Claude]]. #dev", type: "decision", state: "active", space: "UMCP", version: 2 },
  { id: "preview-4", content: "Explore a navigable personal [[Memory Atlas]] inspired by linked notes in [[Obsidian]]. #dev", type: "goal", state: "candidate", space: "UMCP", version: 1 },
  { id: "preview-5", content: "Review the positioning hypothesis for [[UMCP Cloud]] before the next product milestone. #strategy", type: "open_question", state: "stale", space: "Work", version: 2 },
]);

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

export function createAccountPreviewAdapter() {
  let memories = clone(previewMemories);
  let connections = [{ id: "preview-chatgpt", name: "ChatGPT", status: "active", scopes: ["memory:read", "memory:write"], last_used_at: "Today" }, { id: "preview-agent", name: "Personal agent", status: "active", scopes: ["memory:read"], last_used_at: "Yesterday" }];
  let credentials = [];
  return Object.freeze({
    status: "ready",
    features: Object.freeze({ memoryWrite: true, memoryDelete: true, connections: true, agents: true, accountOperations: true }),
    async session() {
      return { preview_mode: true, display_name: "Marcello Franco", email: "preview@umcp.local", subject_id: "preview-subject", tenant_id: "preview-vault", scopes: ["memory:read", "memory:write", "memory:delete"] };
    },
    async listMemories(query = "") {
      const normalized = String(query).trim().toLowerCase();
      const matches = normalized ? memories.filter((memory) => `${memory.content} ${memory.space} ${memory.type}`.toLowerCase().includes(normalized)) : memories;
      return { memories: clone(matches), count: matches.length };
    },
    async getMemory(id) {
      const memory = memories.find((candidate) => candidate.id === id);
      if (!memory) throw new Error("not_found");
      return clone(memory);
    },
    async listConnections() {
      return { connections: clone(connections) };
    },
    async listAgentCredentials() { return { credentials: clone(credentials) }; },
    async capabilities() { return { version: "local-preview", auth: "fixture", email_delivery: "unavailable", tenant_export: false }; },
    async logout() {},
    async createConnection({ name, scopes }) {
      const connection = { id: `preview-connection-${connections.length + 1}`, name: String(name), scopes: clone(scopes), status: "active", last_used_at: null };
      connections.push(connection);
      return { connection: clone(connection) };
    },
    async revokeConnection(id) {
      const connection = connections.find((item) => item.id === id);
      if (!connection) throw new Error("not_found");
      connection.status = "revoked";
      return { connection: clone(connection) };
    },
    async createAgentCredential({ name, scopes, expires_in_seconds }) {
      const credential = { id: `preview-credential-${credentials.length + 1}`, name: String(name), scopes: clone(scopes), expires_in_seconds, revoked: false };
      credentials.push(credential);
      return { credential: clone(credential), token: "umcp_pat_preview_only" };
    },
    async revokeAgentCredential(id) {
      const credential = credentials.find((item) => item.id === id);
      if (!credential) throw new Error("not_found");
      credential.revoked = true;
      return { credential: clone(credential) };
    },
    async updateMemory(id, { expected_version, patch }) {
      const index = memories.findIndex((item) => item.id === id);
      if (index < 0) throw new Error("not_found");
      if (memories[index].version !== expected_version) throw new Error("version_conflict");
      memories[index] = { ...memories[index], ...clone(patch), version: expected_version + 1 };
      return { memory: clone(memories[index]) };
    },
    async forgetMemory(id) {
      const previous = memories.length;
      memories = memories.filter((item) => item.id !== id);
      return { status: memories.length === previous ? "already_absent" : "forgotten" };
    },
    async exportTenant() { return { receipt: { id: "preview-export", status: "accepted" } }; },
    async requestAccountDeletion() { return { receipt: { id: "preview-deletion", status: "accepted" } }; },
  });
}

export function accountPreviewEnabled(scope = globalThis) {
  const hostname = scope.location?.hostname;
  const local = hostname === "localhost" || hostname === "127.0.0.1" || hostname === "[::1]";
  return local && new URLSearchParams(scope.location?.search || "").get("preview") === "account";
}
