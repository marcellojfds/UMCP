# UMCP web experience

This is a dependency-free, mobile-first UI shell for the future Cloud administrative API. It deliberately does **not** implement authentication, authorize a request in the browser, or access PostgreSQL. The server owns those responsibilities under ADR 0011.

Open `index.html` from a local static server for visual review. By default the shell is in `unavailable` mode: it explains the missing backend instead of showing invented memories or pretending an email was sent. The hash routes `#/dashboard`, `#/memories`, `#/connections`, `#/agents`, `#/settings/security`, `#/docs`, and `#/status` provide the server-adapter-gated product surfaces as honest empty states. To connect them, a server-rendered bootstrap may set `window.__UMCP_ADMIN_ADAPTER__` to an adapter implementing the methods documented in `src/admin-adapter.js`.

The browser should only receive a session already established by a server-side, verified callback. The callback return target must be server allowlisted; the UI never accepts an arbitrary redirect URL.
