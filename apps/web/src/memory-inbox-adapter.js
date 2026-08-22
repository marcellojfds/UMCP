import {
  FIXTURE_CONNECTIONS,
  M1_FIXTURE_MEMORY_ID,
  M1_MCP_ENDPOINT,
  M1_TOOL_NAMES,
  clone,
  createFixtureMemory,
} from "./memory-inbox-contract.js";

/**
 * The only integration seam owned by the UI. Core/MCP supplies public M1
 * results through the Streamable HTTP `/mcp` boundary; this adapter maps the
 * frozen tool names without recreating lifecycle or policy in the browser.
 *
 * @param {(tool: string, args: object) => Promise<object>} invokeMcp
 */
export function createM1MemoryInboxAdapter({ invokeMcp, restoreImport, listConnections, revokeConnection, status = "ready" } = {}) {
  if (typeof invokeMcp !== "function") throw new TypeError("invokeMcp is required");
  const invoke = (tool, args) => invokeMcp(tool, args);
  return Object.freeze({
    status,
    endpoint: M1_MCP_ENDPOINT,
    listInbox: ({ space } = {}) => invoke(M1_TOOL_NAMES.listInbox, { ...(space ? { space } : {}) }),
    confirmCandidate: ({ id, expected_version, patch, idempotency_key }) => invoke(M1_TOOL_NAMES.confirm, { id, expected_version, ...(patch ? { patch } : {}), idempotency_key }),
    discardCandidate: ({ id, expected_version, idempotency_key, reason_code = "user_requested_memory" }) => invoke(M1_TOOL_NAMES.discard, { id, expected_version, idempotency_key, reason_code }),
    pinMemory: ({ id, expected_version, pinned, idempotency_key }) => invoke(M1_TOOL_NAMES.pin, { id, expected_version, pinned, idempotency_key }),
    updateMemory: ({ id, expected_version, state, idempotency_key }) => invoke(M1_TOOL_NAMES.update, { id, expected_version, patch: { state }, idempotency_key }),
    recall: ({ query, context_space, include_spaces = [], limit = 10 }) => invoke(M1_TOOL_NAMES.recall, { query, context_space, include_spaces, limit }),
    forgetMemory: ({ id, idempotency_key, reason_code = "user_requested_memory" }) => invoke(M1_TOOL_NAMES.forget, { id, idempotency_key, reason_code }),
    // The frozen M1 tool table has no restore tool. Core/Verification must
    // inject the existing restore/import boundary here to prove tombstones.
    restoreMemory: ({ id }) => typeof restoreImport === "function" ? restoreImport({ id }) : Promise.reject(new Error("restore_import_endpoint_pending")),
    listConnections: () => typeof listConnections === "function" ? listConnections() : Promise.reject(new Error("connections_endpoint_pending")),
    revokeConnection: (id) => typeof revokeConnection === "function" ? revokeConnection(id) : Promise.reject(new Error("connections_endpoint_pending")),
  });
}

/**
 * Deterministic local-only fixture. It mirrors the frozen public result
 * shapes and lifecycle transitions so the Inbox can be reviewed before Core
 * and M1-B are integrated. It never accesses a repository or browser DB.
 */
export function createFixtureMemoryInboxAdapter() {
  let memory = createFixtureMemory();
  let tombstoned = false;
  let connections = clone(FIXTURE_CONNECTIONS);
  let lastRestore = null;
  return {
    status: "fixture",
    endpoint: "fixture://m01-memory-inbox",
    async listInbox() {
      return { candidates: memory?.state === "candidate" ? [clone(memory)] : [], count: memory?.state === "candidate" ? 1 : 0, next_cursor: null };
    },
    async listMemories() {
      return { memories: memory ? [clone(memory)] : [], count: memory ? 1 : 0 };
    },
    async confirmCandidate({ id, expected_version, patch = {} }) {
      if (!memory || memory.id !== id) throw new Error("not_found");
      if (memory.state !== "candidate") throw new Error("invalid_state_transition");
      if (memory.version !== expected_version) throw new Error("version_conflict");
      memory = { ...memory, ...clone(patch), state: "confirmed", version: memory.version + 1 };
      return { memory: clone(memory), status: "confirmed" };
    },
    async discardCandidate({ id, expected_version }) {
      if (!memory || memory.id !== id) return { status: "already_absent", forgotten: false };
      if (memory.version !== expected_version) throw new Error("version_conflict");
      memory = null;
      tombstoned = true;
      return { status: "forgotten", forgotten: true };
    },
    async pinMemory({ id, expected_version, pinned }) {
      if (!memory || memory.id !== id) throw new Error("not_found");
      if (!(["confirmed", "pinned"].includes(memory.state))) throw new Error("invalid_state_transition");
      if (memory.version !== expected_version) throw new Error("version_conflict");
      memory = { ...memory, state: pinned ? "pinned" : "confirmed", version: memory.version + 1 };
      return { memory: clone(memory), status: memory.state };
    },
    async updateMemory({ id, expected_version, state }) {
      if (!memory || memory.id !== id) throw new Error("not_found");
      if (memory.version !== expected_version) throw new Error("version_conflict");
      const nextState = state === "stale" ? "stale" : state === "confirmed" ? "confirmed" : null;
      if (!nextState) throw new Error("invalid_state_transition");
      memory = { ...memory, state: nextState, version: memory.version + 1 };
      return { memory: clone(memory), status: "updated" };
    },
    async recall({ context_space, include_spaces = [] }) {
      const allowed = context_space === "Work" && include_spaces.includes("MBA");
      const eligible = memory && ["confirmed", "pinned"].includes(memory.state) && (memory.space === context_space || allowed);
      const item = eligible ? { memory: clone(memory), reason_retrieved: allowed ? "explicit_cross_space_semantic_match" : "same_space_semantic_match" } : null;
      return { memories: item ? [item] : [], count: item ? 1 : 0, profile: "fixture-contract" };
    },
    async forgetMemory({ id }) {
      if (!memory || memory.id !== id) return { status: "already_absent", forgotten: false };
      memory = null;
      tombstoned = true;
      return { status: "forgotten", forgotten: true };
    },
    async restoreMemory({ id }) {
      if (tombstoned && id === M1_FIXTURE_MEMORY_ID) {
        lastRestore = { status: "restore_blocked_by_tombstone", recreated: false };
        return clone(lastRestore);
      }
      return { status: "restore_not_available", recreated: false };
    },
    async listConnections() {
      return { connections: clone(connections) };
    },
    async revokeConnection(id) {
      const connection = connections.find((candidate) => candidate.id === id);
      if (!connection) throw new Error("not_found");
      connection.status = "revoked";
      return { connection: clone(connection), status: "revoked" };
    },
    async captureMemory({ connection_id = "conn-chatgpt-sim" } = {}) {
      const connection = connections.find((candidate) => candidate.id === connection_id);
      if (connection?.status === "revoked") throw new Error("connection_revoked");
      return { memory: clone(createFixtureMemory()), status: "created" };
    },
    __debug: () => ({ memory: clone(memory), tombstoned, connections: clone(connections), lastRestore: clone(lastRestore) }),
  };
}

let fixtureAdapter;

export function getMemoryInboxAdapter(scope = globalThis) {
  if (scope.__UMCP_M1_INBOX_ADAPTER__?.status) return scope.__UMCP_M1_INBOX_ADAPTER__;
  if (typeof scope.__UMCP_M1_INBOX_INVOKE__ === "function") {
    return createM1MemoryInboxAdapter({ invokeMcp: scope.__UMCP_M1_INBOX_INVOKE__ });
  }
  fixtureAdapter ||= createFixtureMemoryInboxAdapter();
  return fixtureAdapter;
}
