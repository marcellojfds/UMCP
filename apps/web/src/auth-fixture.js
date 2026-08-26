/**
 * H05's browser contract fixture.
 *
 * It mirrors the H04 authorization-code, state, consent and revocation seam
 * without issuing a credential or persisting anything in the browser. A real
 * deployment injects the same shape through __UMCP_H05_AUTH_ADAPTER__.
 */

export const H05_SCOPES = Object.freeze([
  "memory:read",
  "memory:write",
  "memory:delete",
]);

export const H05_CONSENT_REQUEST = Object.freeze({
  request_id: "synthetic-request-001",
  client_id: "synthetic-client",
  client_name: "Local contract fixture",
  purpose: "Review and manage memories for this connection.",
  scopes: H05_SCOPES,
  policy_version: "synthetic-policy-v1",
  connection_id: "synthetic-connection-001",
});

export class AuthFixtureError extends Error {
  constructor(code) {
    super(code);
    this.name = "AuthFixtureError";
    this.code = code;
  }
}

function validEmail(value) {
  return typeof value === "string" && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

function opaque(prefix) {
  const random = globalThis.crypto?.randomUUID?.() || Math.random().toString(36).slice(2);
  return `${prefix}-${random}`;
}

function callbackHash(code, state) {
  return `#/callback?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state)}`;
}

/** Create an isolated in-memory fixture for H05 browser tests and local review. */
export function createSyntheticAuthAdapter({ clock = () => Date.now(), loginTtlMs = 60_000 } = {}) {
  let pending = null;
  let session = null;
  let consent = null;
  let connection = {
    id: H05_CONSENT_REQUEST.connection_id,
    client_id: H05_CONSENT_REQUEST.client_id,
    name: H05_CONSENT_REQUEST.client_name,
    status: "pending",
    scopes: [...H05_SCOPES],
    last_used_at: null,
  };

  function requireSession() {
    if (!session) throw new AuthFixtureError("authentication_required");
    if (connection.status === "revoked") {
      throw new AuthFixtureError("revoked");
    }
    return { ...session };
  }

  function beginLogin({ method, email } = {}) {
    if (method !== "google" && method !== "magic_link") {
      throw new AuthFixtureError("unsupported_login_method");
    }
    if (method === "magic_link" && !validEmail(email)) {
      throw new AuthFixtureError("invalid_email");
    }
    const state = opaque("synthetic-state");
    const code = opaque("synthetic-code");
    pending = { method, state, code, expires_at: clock() + loginTtlMs, used: false };
    const result = { status: method === "magic_link" ? "accepted" : "redirected", mode: "fixture" };
    if (method === "google") result.callback_hash = callbackHash(code, state);
    return result;
  }

  function openCapturedLink() {
    if (!pending || pending.method !== "magic_link") {
      throw new AuthFixtureError("magic_link_unavailable");
    }
    return callbackHash(pending.code, pending.state);
  }

  function completeCallback({ code, state } = {}) {
    if (!pending || pending.used || pending.code !== code || pending.state !== state) {
      throw new AuthFixtureError("invalid_callback");
    }
    if (pending.expires_at <= clock()) {
      pending.used = true;
      throw new AuthFixtureError("expired_callback");
    }
    pending.used = true;
    session = {
      subject_id: "synthetic-subject-001",
      tenant_id: "synthetic-tenant-001",
      consent_id: null,
    };
    return { status: "authenticated", next: "consent" };
  }

  function consentRequest() {
    requireSession();
    if (consent) throw new AuthFixtureError("consent_already_decided");
    return { ...H05_CONSENT_REQUEST, scopes: [...H05_CONSENT_REQUEST.scopes] };
  }

  function grantConsent() {
    requireSession();
    if (consent) throw new AuthFixtureError("consent_already_decided");
    consent = {
      consent_id: "synthetic-consent-001",
      subject_id: session.subject_id,
      client_id: H05_CONSENT_REQUEST.client_id,
      scopes: [...H05_SCOPES],
      policy_version: H05_CONSENT_REQUEST.policy_version,
      version: 1,
      granted_at: new Date(clock()).toISOString(),
      connection_id: H05_CONSENT_REQUEST.connection_id,
    };
    connection = { ...connection, status: "active" };
    session = { ...session, consent_id: consent.consent_id };
    return { status: "granted", consent: { ...consent }, connection: { ...connection } };
  }

  function denyConsent() {
    requireSession();
    consent = { status: "denied" };
    session = null;
    return { status: "denied" };
  }

  function listConnections() {
    requireSession();
    return { connections: [{ ...connection, scopes: [...connection.scopes] }], count: 1 };
  }

  function revokeConnection(id) {
    requireSession();
    if (id !== connection.id) throw new AuthFixtureError("not_found");
    connection = { ...connection, status: "revoked" };
    return { status: "revoked", connection: { ...connection } };
  }

  return Object.freeze({
    status: "ready",
    mode: "fixture",
    provider: "synthetic",
    beginLogin,
    openCapturedLink,
    completeCallback,
    consentRequest,
    grantConsent,
    denyConsent,
    session: requireSession,
    listConnections,
    revokeConnection,
  });
}

export const unavailableAuthAdapter = Object.freeze({
  status: "unavailable",
  mode: "unavailable",
});

let localFixture = createSyntheticAuthAdapter();

export function getAuthAdapter(scope = globalThis) {
  const adapter = scope.__UMCP_H05_AUTH_ADAPTER__;
  if (adapter && adapter.status === "ready") return adapter;
  return localFixture;
}

export function resetAuthFixture() {
  localFixture = createSyntheticAuthAdapter();
}
