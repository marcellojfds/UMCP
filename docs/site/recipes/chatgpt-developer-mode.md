# ChatGPT developer-mode recipe (not yet verified)

**Prerequisite:** an authorized deployment exposes the MCP protocol only at a
stable HTTPS `/mcp` endpoint and its OAuth/protected-resource metadata. Do not
use a local tunnel as a public endpoint or mark this recipe Supported from a
tunnel-only test.

1. Record the exact ChatGPT version/date and gateway SHA in a conformance
   report.
2. Create a test tenant through the deployed, server-side auth flow.
3. Connect the `/mcp` endpoint through the documented developer-mode flow and
   approve the minimum requested scopes.
4. Run the positive and destructive prompts in
   [`examples/conformance/prompts.md`](../../../examples/conformance/prompts.md).
5. Revoke the connection; confirm that its credential fails safely and no
   tenant identifier supplied by the client changes the result.
6. Attach the redacted report and only then promote the matrix row.

Never paste access tokens, memory text, real email addresses, or production
URLs into a report.
