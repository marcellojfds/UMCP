/**
 * Browser boundary for the separately versioned administrative API (ADR 0010).
 * A trusted server injects this adapter after session verification. It must
 * derive principal and tenant from the session; no method accepts owner_id.
 */
export const unavailableAdapter = Object.freeze({
  status: "unavailable",
  async listMemories() { throw new Error("The authenticated administrative API is not available."); },
  async requestMagicLink() { throw new Error("The server-side email flow is not available."); },
  async exportTenant() { throw new Error("The authenticated administrative API is not available."); },
  async requestAccountDeletion() { throw new Error("The authenticated administrative API is not available."); },
  async revokeConnection() { throw new Error("The authenticated administrative API is not available."); },
});

export function getAdminAdapter(scope = globalThis) {
  const adapter = scope.__UMCP_ADMIN_ADAPTER__;
  return adapter && adapter.status === "ready" ? adapter : unavailableAdapter;
}
