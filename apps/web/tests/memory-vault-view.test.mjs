import test from "node:test";
import assert from "node:assert/strict";
import { filterMemories, memoryViewHash, renderAccountInbox, renderMemoryBrowser } from "../src/memory-vault-view.js";

const memories = [
  { id: "1", content: "A", type: "lesson", state: "candidate", space: "MBA", version: 1 },
  { id: "2", content: "B", type: "preference", state: "pinned", space: "Work", version: 2 },
  { id: "3", content: "C", type: "lesson", state: "stale", space: "Work", version: 1 },
];

test("memory filters combine space, state, and type without changing source data", () => {
  assert.deepEqual(filterMemories(memories, { space: "Work", type: "lesson" }).map(({ id }) => id), ["3"]);
  assert.equal(memories.length, 3);
});

test("memory browser exposes working view links and preserves active filters", () => {
  const view = renderMemoryBrowser({ items: memories, query: "memory", space: "Work", state: "stale", view: "list" });
  assert.match(view.content, /1 of 3 memory/);
  assert.match(view.content, /vault-memory-grid is-list/);
  assert.match(view.toolbar, /view=cards|Card view/);
  assert.equal(memoryViewHash({ query: "memory", space: "Work", view: "list" }), "#/memories?query=memory&space=Work&view=list");
});

test("account inbox contains only memories that need a decision", () => {
  const html = renderAccountInbox(memories);
  assert.match(html, /2 memories need/);
  assert.match(html, />A</);
  assert.match(html, />C</);
  assert.doesNotMatch(html, />B</);
});

test("memory browser renders calm empty vault without filter controls when 0 memories exist", () => {
  const view = renderMemoryBrowser({ items: [], query: "", space: "", state: "", type: "", view: "cards" });
  assert.match(view.content, /Your memory vault is empty/);
  assert.doesNotMatch(view.content, /vault-filterbar/);
  assert.equal(view.toolbar, "");
});
