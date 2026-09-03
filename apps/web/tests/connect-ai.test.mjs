import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const html = await readFile(new URL("../index.html", import.meta.url), "utf8");

test("public landing page contains an actionable Claude Code OAuth recipe", () => {
  assert.match(html, /claude mcp add --transport http --scope user/);
  assert.match(html, /--client-id umcp-claude-code --callback-port 17171/);
  assert.match(html, /claude mcp login umcp/);
  assert.match(html, /claude mcp list/);
  assert.match(html, /approved before OAuth will grant access/);
  assert.match(html, /Claude Pro or Max account, or an Anthropic API key/);
});

test("Claude guidance does not confuse the hosted endpoint with local stdio", () => {
  const claudeCard = html.match(/<article class="ai-card ai-card--wide">[\s\S]*?<\/article>/)?.[0];
  assert.ok(claudeCard);
  assert.doesNotMatch(claudeCard, /python3 -m omp\.server/);
  assert.doesNotMatch(claudeCard, /Claude Desktop \/ Code/);
  assert.match(claudeCard, /https:\/\/umcp-cloud-staging-[^< ]+\/mcp/);
});
