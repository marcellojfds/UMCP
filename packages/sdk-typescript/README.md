# UMCP TypeScript SDK scaffold

This experimental package is transport-agnostic. Provide an authenticated MCP
transport from the approved gateway/client runtime; the SDK does not implement
OAuth, retain credentials, use `owner_id`, or access the database.

```js
import { createMemoryClient } from "@umcp/sdk";
const client = createMemoryClient(authenticatedMcpTransport);
await client.write({ content: "Synthetic preference", type: "preference" }, "example-write-1");
await client.search({ query: "preference", limit: 5 });
```

The authenticated transport is pending Terra’s Streamable HTTP implementation.
Never embed bearer tokens in browser bundles or source files.
