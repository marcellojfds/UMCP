import test from "node:test";
import assert from "node:assert/strict";
import { createHttpAdminAdapter, getAdminAdapter, unavailableAdapter } from "../src/admin-adapter.js";

test("browser bootstrap enables only an explicitly configured same-origin Admin API", () => {
  assert.equal(getAdminAdapter({}).status, "unavailable");
  assert.equal(getAdminAdapter({ __UMCP_ADMIN_API_BASE_URL__: "//example.test" }), unavailableAdapter);
  assert.equal(getAdminAdapter({ __UMCP_ADMIN_API_BASE_URL__: "/admin" }).status, "ready");
  assert.equal(getAdminAdapter({ __UMCP_ADMIN_API_BASE_URL__: "/portal" }).features.memoryWrite, false);
});

test("account preview is opt-in and restricted to local hosts", async () => {
  const scope = { location: { hostname: "127.0.0.1", search: "?preview=account" } };
  const local = getAdminAdapter(scope);
  assert.equal(local.status, "ready");
  assert.equal((await local.session()).preview_mode, true);
  const original = await local.getMemory("preview-1");
  await local.updateMemory(original.id, { expected_version: original.version, patch: { content: "Updated preview" } });
  assert.equal((await getAdminAdapter(scope).getMemory("preview-1")).content, "Updated preview");
  assert.equal(getAdminAdapter({ location: { hostname: "umcp.example", search: "?preview=account" } }), unavailableAdapter);
});

test("HTTP adapter carries CSRF only after verified callback", async () => {
  const requests = [];
  const adapter = createHttpAdminAdapter({ fetchImpl: async (url, options) => {
    requests.push({ url, options });
    return new Response(JSON.stringify(url.includes("callback") ? { csrf: "csrf-1" } : { status: "ok" }), { status: 200 });
  }});
  await adapter.requestMagicLink({ email: "synthetic@example.test" });
  assert.equal(requests[0].options.headers["x-umcp-csrf"], undefined);
  await adapter.completeMagicLink("single-use-token");
  await adapter.logout();
  assert.equal(requests[2].options.headers["x-umcp-csrf"], "csrf-1");
});

test("HTTP adapter preserves authentication failures for a useful sign-in state", async () => {
  const adapter = createHttpAdminAdapter({ baseUrl: "/portal", fetchImpl: async () => new Response(JSON.stringify({ error: "authentication_required" }), { status: 401 }) });
  await assert.rejects(() => adapter.session(), (error) => error.code === "authentication_required" && error.status === 401);
});

test("portal adapter refreshes an expired session once and retries the request", async () => {
  const requests = [];
  const adapter = createHttpAdminAdapter({ baseUrl: "/portal", fetchImpl: async (url, options) => {
    requests.push({ url, options });
    if (url === "/portal/api/refresh") return new Response("{}", { status: 200 });
    if (requests.filter((item) => item.url === "/portal/api/session").length === 1) {
      return new Response(JSON.stringify({ error: "authentication_required" }), { status: 401 });
    }
    return new Response(JSON.stringify({ subject_id: "subject", tenant_id: "tenant" }), { status: 200 });
  }});
  assert.equal((await adapter.session()).subject_id, "subject");
  assert.deepEqual(requests.map(({ url }) => url), [
    "/portal/api/session",
    "/portal/api/refresh",
    "/portal/api/session",
  ]);
});

test("HTTP adapter exposes only server-owned control-plane paths", async () => {
  const requests = [];
  const adapter = createHttpAdminAdapter({ fetchImpl: async (url, options) => {
    requests.push({ url, options });
    return new Response(JSON.stringify(url.includes("callback") ? { csrf: "csrf-1" } : { status: "ok" }), { status: 200 });
  }});
  await adapter.completeMagicLink("single-use-token");
  await adapter.createConnection({ name: "agent", scopes: ["memory:read"] });
  await adapter.revokeConnection("conn/id");
  await adapter.updateMemory("memory/id", {
    expected_version: 2,
    patch: { content: "updated" },
    idempotency_key: "update-1",
  });
  await adapter.forgetMemory("memory/id", "forget-1");
  await adapter.exportTenant();
  assert.deepEqual(requests.slice(1).map(({ url }) => url), [
    "/api/connections",
    "/api/connections/conn%2Fid/revoke",
    "/api/memories/memory%2Fid",
    "/api/memories/memory%2Fid?idempotency_key=forget-1",
    "/api/exports",
  ]);
  assert.equal(requests[1].options.headers["x-umcp-csrf"], "csrf-1");
  assert.equal(requests[3].options.headers["x-umcp-csrf"], "csrf-1");
});
