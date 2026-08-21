import test from "node:test";
import assert from "node:assert/strict";
import { createHttpAdminAdapter } from "../src/admin-adapter.js";

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
