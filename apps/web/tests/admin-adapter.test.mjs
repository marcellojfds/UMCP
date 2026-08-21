import test from "node:test";
import assert from "node:assert/strict";
import { createHttpAdminAdapter, getAdminAdapter, unavailableAdapter } from "../src/admin-adapter.js";

test("browser bootstrap enables only an explicitly configured same-origin Admin API", () => {
  assert.equal(getAdminAdapter({}).status, "unavailable");
  assert.equal(getAdminAdapter({ __UMCP_ADMIN_API_BASE_URL__: "//example.test" }), unavailableAdapter);
  assert.equal(getAdminAdapter({ __UMCP_ADMIN_API_BASE_URL__: "/admin" }).status, "ready");
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

test("HTTP adapter exposes only server-owned control-plane paths", async () => {
  const requests = [];
  const adapter = createHttpAdminAdapter({ fetchImpl: async (url, options) => {
    requests.push({ url, options });
    return new Response(JSON.stringify(url.includes("callback") ? { csrf: "csrf-1" } : { status: "ok" }), { status: 200 });
  }});
  await adapter.completeMagicLink("single-use-token");
  await adapter.createConnection({ name: "agent", scopes: ["memory:read"] });
  await adapter.revokeConnection("conn/id");
  await adapter.exportTenant();
  assert.deepEqual(requests.slice(1).map(({ url }) => url), [
    "/api/connections",
    "/api/connections/conn%2Fid/revoke",
    "/api/exports",
  ]);
  assert.equal(requests[1].options.headers["x-umcp-csrf"], "csrf-1");
});
