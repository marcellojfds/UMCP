import assert from "node:assert/strict";
import test from "node:test";
import { createMemoryClient } from "../src/client.js";

test("write forwards an idempotency key and never an owner id", async () => {
  const calls = [];
  const client = createMemoryClient({ callTool: async (...args) => { calls.push(args); return { ok: true }; } });
  await client.write({ content: "synthetic", type: "preference" }, "write-1");
  assert.deepEqual(calls, [["memory.write", { content: "synthetic", type: "preference" }, { idempotencyKey: "write-1" }]]);
  assert.throws(() => client.search({ owner_id: "forged", query: "x" }), /owner_id/);
});

test("destructive calls require an idempotency key", () => {
  const client = createMemoryClient({ callTool: async () => ({ ok: true }) });
  assert.throws(() => client.forget({ memory_id: "m-1" }, ""), /idempotency/);
});
