import test from "node:test";
import assert from "node:assert/strict";
import { createFixtureMemoryInboxAdapter, createM1MemoryInboxAdapter } from "../src/memory-inbox-adapter.js";
import { M1_FIXTURE_MEMORY_ID, M1_MCP_ENDPOINT, M1_TOOL_NAMES, createFixtureMemory } from "../src/memory-inbox-contract.js";
import { renderMemoryInbox } from "../src/memory-inbox-view.js";

test("fixture preserves the frozen provenance and consent shapes", () => {
  const memory = createFixtureMemory();
  assert.equal(memory.state, "candidate");
  assert.equal(memory.space, "MBA");
  assert.equal(memory.provenance.source_client, "chatgpt-sim");
  assert.equal(memory.provenance.source_type, "conversation");
  assert.equal(memory.provenance.captured_at, "2026-08-22T12:00:00Z");
  assert.equal(memory.capture_consent.mode, "assisted");
  assert.equal(memory.capture_consent.reason_code, "user_requested_memory");
});

test("fixture exercises candidate, confirmation, pin, stale review, recall, forget and tombstone restore", async () => {
  const adapter = createFixtureMemoryInboxAdapter();
  const initial = await adapter.listInbox({ space: "MBA" });
  assert.equal(initial.count, 1);
  assert.equal(initial.candidates[0].state, "candidate");
  assert.equal((await adapter.recall({ context_space: "Work", include_spaces: ["MBA"] })).count, 0);

  const confirmed = await adapter.confirmCandidate({ id: M1_FIXTURE_MEMORY_ID, expected_version: 1, patch: { content: "Edited lesson." }, idempotency_key: "confirm-1" });
  assert.equal(confirmed.memory.state, "confirmed");
  assert.equal(confirmed.memory.version, 2);
  assert.equal(confirmed.memory.provenance.source_client, "chatgpt-sim");
  assert.equal(confirmed.memory.capture_consent.mode, "assisted");

  const pinned = await adapter.pinMemory({ id: M1_FIXTURE_MEMORY_ID, expected_version: 2, pinned: true, idempotency_key: "pin-1" });
  assert.equal(pinned.memory.state, "pinned");
  const stale = await adapter.updateMemory({ id: M1_FIXTURE_MEMORY_ID, expected_version: 3, state: "stale", idempotency_key: "stale-1" });
  assert.equal(stale.memory.state, "stale");
  const reviewed = await adapter.updateMemory({ id: M1_FIXTURE_MEMORY_ID, expected_version: 4, state: "confirmed", idempotency_key: "review-1" });
  assert.equal(reviewed.memory.state, "confirmed");
  const recalled = await adapter.recall({ query: "incentives outcome", context_space: "Work", include_spaces: ["MBA"] });
  assert.equal(recalled.count, 1);
  assert.equal(recalled.memories[0].reason_retrieved, "explicit_cross_space_semantic_match");

  assert.deepEqual(await adapter.forgetMemory({ id: M1_FIXTURE_MEMORY_ID, idempotency_key: "forget-1" }), { status: "forgotten", forgotten: true });
  assert.deepEqual(await adapter.forgetMemory({ id: M1_FIXTURE_MEMORY_ID, idempotency_key: "forget-2" }), { status: "already_absent", forgotten: false });
  assert.deepEqual(await adapter.restoreMemory({ id: M1_FIXTURE_MEMORY_ID }), { status: "restore_blocked_by_tombstone", recreated: false });
  assert.equal((await adapter.recall({ context_space: "Work", include_spaces: ["MBA"] })).count, 0);
});

test("fixture revocation is scoped to the named connection", async () => {
  const adapter = createFixtureMemoryInboxAdapter();
  await adapter.revokeConnection("conn-chatgpt-sim");
  await assert.rejects(() => adapter.captureMemory({ connection_id: "conn-chatgpt-sim" }), /connection_revoked/);
  const connections = await adapter.listConnections();
  assert.equal(connections.connections.find((item) => item.id === "conn-chatgpt-sim").status, "revoked");
  assert.equal(connections.connections.find((item) => item.id === "conn-claude-sim").status, "active");
});

test("M1 adapter maps only frozen MCP tool names and leaves restore/connections explicit", async () => {
  const calls = [];
  const adapter = createM1MemoryInboxAdapter({
    invokeMcp: async (tool, args) => { calls.push({ tool, args }); return { tool }; },
    restoreImport: async ({ id }) => ({ status: "restore_blocked_by_tombstone", id }),
    listConnections: async () => ({ connections: [] }),
    revokeConnection: async (id) => ({ status: "revoked", id }),
  });
  assert.equal(adapter.endpoint, M1_MCP_ENDPOINT);
  await adapter.listInbox({ space: "MBA" });
  await adapter.confirmCandidate({ id: "id", expected_version: 1, idempotency_key: "k" });
  await adapter.pinMemory({ id: "id", expected_version: 2, pinned: true, idempotency_key: "k2" });
  await adapter.recall({ query: "q", context_space: "Work", include_spaces: ["MBA"] });
  await adapter.forgetMemory({ id: "id", idempotency_key: "k3" });
  assert.deepEqual(calls.map(({ tool }) => tool), [M1_TOOL_NAMES.listInbox, M1_TOOL_NAMES.confirm, M1_TOOL_NAMES.pin, M1_TOOL_NAMES.recall, M1_TOOL_NAMES.forget]);
  assert.deepEqual(await adapter.restoreMemory({ id: "id" }), { status: "restore_blocked_by_tombstone", id: "id" });
});

test("Inbox view exposes loading, empty, error, lifecycle and recall feedback states", () => {
  assert.match(renderMemoryInbox({ state: "loading" }), /LOADING MEMORY INBOX/);
  assert.match(renderMemoryInbox({ state: "error" }), /Retry/);
  assert.match(renderMemoryInbox({ state: "success", candidates: [] }), /INBOX EMPTY/);
  const memory = createFixtureMemory();
  assert.match(renderMemoryInbox({ state: "success", candidates: [memory], memories: [memory], connections: [] }), /Confirm candidate/);
  const confirmed = { ...memory, state: "confirmed", version: 2 };
  assert.match(renderMemoryInbox({ state: "success", candidates: [], memories: [confirmed], connections: [], recall: { count: 1, memories: [{ memory: confirmed, reason_retrieved: "explicit_cross_space_semantic_match" }] } }), /explicit_cross_space_semantic_match/);
  assert.match(renderMemoryInbox({ state: "success", candidates: [], memories: [], connections: [], restore: { status: "restore_blocked_by_tombstone", recreated: false } }), /restore_blocked_by_tombstone/);
});
