# UMCP web experience

This is a dependency-free, mobile-first UI shell for the future Cloud administrative API. It deliberately does **not** implement authentication, authorize a request in the browser, or access PostgreSQL. The server owns those responsibilities under ADR 0011.

Open `index.html` from a local static server for visual review. By default the shell is in `unavailable` mode: it explains the missing backend instead of showing invented memories or pretending an email was sent. The hash routes `#/dashboard`, `#/memories`, `#/connections`, `#/agents`, `#/settings/security`, `#/docs`, and `#/status` provide the server-adapter-gated product surfaces as honest empty states. A same-origin Admin API can opt in through `window.__UMCP_ADMIN_API_BASE_URL__ = "/admin"`; the browser adapter then calls only its server-owned `/api/*` endpoints and relies on its HttpOnly session cookie. A server-rendered bootstrap may alternatively set `window.__UMCP_ADMIN_ADAPTER__` to a compatible adapter. No browser bootstrap may provide a bearer token, tenant, or owner identifier.

The browser should only receive a session already established by a server-side, verified callback. The callback return target must be server allowlisted; the UI never accepts an arbitrary redirect URL.

## M01 Memory Inbox preview

Open `#/inbox` to review the independent M1-C experience. It starts on a deterministic synthetic fixture and exercises the frozen `candidate`, `confirmed`, `pinned`, and `stale` lifecycle, separate provenance/consent metadata, bounded `reason_retrieved`, per-connection revoke, terminal forget, and tombstone-blocked restore/import. The fixture is not product evidence or a substitute for Core/M1-B.

Integration injects `window.__UMCP_M1_INBOX_ADAPTER__` or `window.__UMCP_M1_INBOX_INVOKE__`. The adapter maps the exact public M1 tools to the Streamable HTTP `/mcp` boundary: `memory.inbox.list`, `memory.inbox.confirm`, `memory.inbox.discard`, `memory.pin`, `memory.recall`, `memory.update`, and `memory.forget`. Restore/import and connection controls remain explicit injected seams because they are not new M1 MCP tools in the frozen contract.
