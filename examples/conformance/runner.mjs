#!/usr/bin/env node
// Provider-neutral lifecycle runner. Usage: node runner.mjs ./adapter.mjs
// Adapter exports createTransport(), returning listTools() and callTool().
import { pathToFileURL } from "node:url";

const adapterPath = process.argv[2];
if (!adapterPath) throw new Error("Usage: node runner.mjs ./adapter.mjs");
const adapterUrl = pathToFileURL(new URL(adapterPath, pathToFileURL(`${process.cwd()}/`)).pathname);
const { createTransport } = await import(adapterUrl);
const transport = await createTransport();
const expected = ["memory.write", "memory.search", "memory.update", "memory.forget"];
const tools = await transport.listTools();
const names = new Set(tools.map((tool) => tool.name));
for (const name of expected) if (!names.has(name)) throw new Error(`Missing tool: ${name}`);
const runId = `conformance-${Date.now()}`;
const created = await transport.callTool("memory.write", { content: "Synthetic conformance memory", type: "preference", provenance: { source_type: "test", captured_at: "2026-08-21T00:00:00Z" } }, { idempotencyKey: `${runId}-write` });
const memoryId = created.memory_id ?? created.id;
if (!memoryId) throw new Error("write did not return a memory identifier");
const searched = await transport.callTool("memory.search", { query: "Synthetic conformance memory", limit: 5 });
if (!JSON.stringify(searched).includes(memoryId)) throw new Error("search did not return the written memory");
await transport.callTool("memory.update", { memory_id: memoryId, content: "Synthetic corrected conformance memory" }, { idempotencyKey: `${runId}-update` });
await transport.callTool("memory.forget", { memory_id: memoryId }, { idempotencyKey: `${runId}-forget` });
console.log(JSON.stringify({ status: "pass", run_id: runId, tools: expected, note: "No payloads, tokens, emails, or tenant identifiers were emitted." }));
