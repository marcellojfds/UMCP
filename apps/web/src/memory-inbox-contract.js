/**
 * UI-facing M01 contract types. These are deliberately JSDoc types: the web
 * shell has no runtime dependency on Core or the MCP server while M1 is being
 * integrated.
 */

/** @typedef {Object} Provenance
 * @property {"conversation"|string} source_type
 * @property {string} source_client
 * @property {string=} source_connection_id
 * @property {string=} conversation_id
 * @property {string=} message_id
 * @property {string=} source_model
 * @property {string} captured_at
 * @property {string[]=} evidence
 */

/** @typedef {Object} CaptureConsent
 * @property {"manual"|"assisted"|"automatic"|"legacy_unverified"} mode
 * @property {string} consent_id
 * @property {"user_requested_memory"|"user_confirmed_inbox"|"connection_policy_automatic"|"import_authorized"} reason_code
 * @property {string} policy_version
 * @property {string} granted_at
 */

/** @typedef {Object} MemorySnapshot
 * @property {string} id
 * @property {string} content
 * @property {string} type
 * @property {number} version
 * @property {"candidate"|"confirmed"|"pinned"|"stale"|"superseded"|"contradicted"|"archived"} state
 * @property {string|null} space
 * @property {Provenance} provenance
 * @property {CaptureConsent} capture_consent
 */

/** @typedef {Object} ConnectionSnapshot
 * @property {string} id
 * @property {string} name
 * @property {"active"|"revoked"} status
 * @property {string[]} scopes
 */

/** @typedef {Object} RecallItem
 * @property {MemorySnapshot} memory
 * @property {string} reason_retrieved
 */

export const M1_MEMORY_STATES = Object.freeze(["candidate", "confirmed", "pinned", "stale", "superseded", "contradicted", "archived"]);
export const M1_MCP_ENDPOINT = "/mcp";
export const M1_TOOL_NAMES = Object.freeze({
  listInbox: "memory.inbox.list",
  confirm: "memory.inbox.confirm",
  discard: "memory.inbox.discard",
  pin: "memory.pin",
  recall: "memory.recall",
  update: "memory.update",
  forget: "memory.forget",
});

export const M1_FIXTURE_MEMORY_ID = "memory-m1-lesson-001";

/** @returns {MemorySnapshot} */
export function createFixtureMemory() {
  return {
    id: M1_FIXTURE_MEMORY_ID,
    content: "Incentives mal designed make teams optimize the metric, not the outcome.",
    type: "lesson",
    version: 1,
    state: "candidate",
    space: "MBA",
    provenance: {
      source_type: "conversation",
      source_client: "chatgpt-sim",
      source_connection_id: "conn-chatgpt-sim",
      conversation_id: "conv-opaque-001",
      message_id: "msg-opaque-007",
      source_model: "model-opaque",
      captured_at: "2026-08-22T12:00:00Z",
      evidence: ["user-selected-excerpt-1"],
    },
    capture_consent: {
      mode: "assisted",
      consent_id: "consent-opaque-001",
      reason_code: "user_requested_memory",
      policy_version: "m1-local-1",
      granted_at: "2026-08-22T12:00:00Z",
    },
  };
}

export const FIXTURE_CONNECTIONS = Object.freeze([
  { id: "conn-chatgpt-sim", name: "chatgpt-sim", status: "active", scopes: ["memory:read", "memory:write", "memory:delete"] },
  { id: "conn-claude-sim", name: "claude-sim", status: "active", scopes: ["memory:read", "memory:write", "memory:delete"] },
]);

export function clone(value) {
  return value === undefined ? undefined : JSON.parse(JSON.stringify(value));
}
