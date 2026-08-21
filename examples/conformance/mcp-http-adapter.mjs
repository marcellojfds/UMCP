// Loopback-only Streamable HTTP adapter for the provider-neutral lifecycle runner.
// Set UMCP_MCP_URL and UMCP_ACCESS_TOKEN; this module never logs either value.

const endpoint = process.env.UMCP_MCP_URL;
const accessToken = process.env.UMCP_ACCESS_TOKEN;

function required(value, name) {
  if (!value) throw new Error(`${name} is required`);
  return value;
}

function localEndpoint(value) {
  const url = new URL(required(value, "UMCP_MCP_URL"));
  if (url.protocol !== "http:" || !["127.0.0.1", "localhost"].includes(url.hostname)) {
    throw new Error("conformance adapter only permits local HTTP loopback");
  }
  return url;
}

async function parseResponse(response) {
  const body = await response.text();
  if (!response.ok) throw new Error(`MCP request failed (${response.status})`);
  const data = body.startsWith("event:")
    ? body.split("\n").find((line) => line.startsWith("data:"))?.slice(5).trim()
    : body;
  if (!data) throw new Error("MCP response was empty");
  return JSON.parse(data);
}

function toolArguments(name, input, options = {}) {
  if (name === "memory.write") return { ...input, idempotency_key: options.idempotencyKey };
  if (name === "memory.update") {
    return {
      id: input.memory_id,
      expected_version: input.expected_version ?? 1,
      patch: { content: input.content },
      idempotency_key: options.idempotencyKey,
    };
  }
  if (name === "memory.forget") return { id: input.memory_id, idempotency_key: options.idempotencyKey };
  return input;
}

export async function createTransport() {
  const url = localEndpoint(endpoint);
  const token = required(accessToken, "UMCP_ACCESS_TOKEN");
  let requestId = 0;
  async function rpc(method, params) {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        authorization: `Bearer ${token}`,
        accept: "application/json, text/event-stream",
        "content-type": "application/json",
      },
      body: JSON.stringify({ jsonrpc: "2.0", id: ++requestId, method, params }),
    });
    const message = await parseResponse(response);
    if (message.error) throw new Error("MCP returned a safe protocol error");
    return message.result;
  }
  await rpc("initialize", {
    protocolVersion: "2025-11-25",
    capabilities: {},
    clientInfo: { name: "umcp-local-conformance", version: "0.1" },
  });
  return {
    async listTools() { return (await rpc("tools/list", {})).tools; },
    async callTool(name, input, options) {
      const result = await rpc("tools/call", { name, arguments: toolArguments(name, input, options) });
      if (result.isError) throw new Error("MCP tool call failed");
      const envelope = JSON.parse(result.content[0].text);
      if (!envelope.ok) throw new Error("UMCP tool call failed");
      if (name === "memory.write" || name === "memory.update") return envelope.data.memory;
      return envelope.data;
    },
  };
}
