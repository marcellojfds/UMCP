function requireIdempotencyKey(value) {
  if (typeof value !== "string" || value.trim().length < 1) throw new TypeError("A non-empty idempotency key is required for write, update, and forget.");
}

function assertCloudInput(input) {
  if (!input || typeof input !== "object" || Array.isArray(input)) throw new TypeError("Tool input must be an object.");
  if (Object.hasOwn(input, "owner_id")) throw new TypeError("owner_id is not accepted by the hosted SDK; the gateway derives tenant identity from the verified credential.");
}

export function createMemoryClient(transport) {
  if (!transport || typeof transport.callTool !== "function") throw new TypeError("A MCP transport with callTool is required.");
  const call = (name, input, idempotencyKey) => { assertCloudInput(input); return transport.callTool(name, input, idempotencyKey ? { idempotencyKey } : undefined); };
  return Object.freeze({
    search(input) { return call("memory.search", input); },
    write(input, idempotencyKey) { requireIdempotencyKey(idempotencyKey); return call("memory.write", input, idempotencyKey); },
    update(input, idempotencyKey) { requireIdempotencyKey(idempotencyKey); return call("memory.update", input, idempotencyKey); },
    forget(input, idempotencyKey) { requireIdempotencyKey(idempotencyKey); return call("memory.forget", input, idempotencyKey); },
  });
}
