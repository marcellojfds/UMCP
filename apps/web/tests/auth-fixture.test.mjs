import test from "node:test";
import assert from "node:assert/strict";
import { AuthFixtureError, H05_SCOPES, createSyntheticAuthAdapter } from "../src/auth-fixture.js";

function callbackParts(value) {
  const query = value.slice(value.indexOf("?") + 1);
  return Object.fromEntries(new URLSearchParams(query));
}

test("synthetic login uses a one-time state-bound callback for Google and magic link", async () => {
  const adapter = createSyntheticAuthAdapter();
  const google = adapter.beginLogin({ method: "google" });
  const callback = callbackParts(google.callback_hash);
  assert.equal(google.mode, "fixture");
  assert.deepEqual(await adapter.completeCallback(callback), { status: "authenticated", next: "consent" });
  assert.throws(() => adapter.completeCallback(callback), (error) => error instanceof AuthFixtureError && error.code === "invalid_callback");

  const second = createSyntheticAuthAdapter();
  const magic = second.beginLogin({ method: "magic_link", email: "person@example.test" });
  assert.deepEqual(magic, { status: "accepted", mode: "fixture" });
  assert.match(second.openCapturedLink(), /^#\/callback\?/);
});

test("synthetic callback fails closed for a wrong state and expiry", () => {
  let now = 10_000;
  const adapter = createSyntheticAuthAdapter({ clock: () => now, loginTtlMs: 100 });
  const callback = callbackParts(adapter.beginLogin({ method: "google" }).callback_hash);
  assert.throws(() => adapter.completeCallback({ ...callback, state: "forged" }), /invalid_callback/);
  now += 101;
  assert.throws(() => adapter.completeCallback(callback), /expired_callback/);
  assert.throws(() => adapter.session(), /authentication_required/);
});

test("consent is server-shaped, cannot be expanded by the browser, and creates a revocable connection", () => {
  const adapter = createSyntheticAuthAdapter();
  const callback = callbackParts(adapter.beginLogin({ method: "google" }).callback_hash);
  adapter.completeCallback(callback);
  const request = adapter.consentRequest();
  assert.deepEqual(request.scopes, H05_SCOPES);
  const granted = adapter.grantConsent({ scopes: ["tenant:admin"] });
  assert.deepEqual(granted.consent.scopes, H05_SCOPES);
  assert.equal(granted.connection.status, "active");
  assert.equal(adapter.listConnections().connections[0].last_used_at, null);

  assert.deepEqual(adapter.revokeConnection(granted.connection.id).connection.status, "revoked");
  assert.throws(() => adapter.session(), /revoked/);
});

test("denying consent creates no connection and returns to an unauthenticated state", () => {
  const adapter = createSyntheticAuthAdapter();
  const callback = callbackParts(adapter.beginLogin({ method: "magic_link", email: "person@example.test" }).callback_hash || adapter.openCapturedLink());
  adapter.completeCallback(callback);
  assert.deepEqual(adapter.denyConsent(), { status: "denied" });
  assert.throws(() => adapter.session(), /authentication_required/);
});
