# Compatibility matrix

**Last reviewed:** 2026-08-21  
**Report policy:** a row becomes **Supported** only after a dated, authenticated
conformance report records `write → search → update → forget`, appropriate
scopes, revocation, and destructive-action behavior where the client exposes
confirmation. No Cloud endpoint currently exists; consequently no row is
Supported.

| Surface | Transport / auth target | Lifecycle status | Limit / recipe |
| --- | --- | --- | --- |
| ChatGPT developer mode | HTTPS Streamable HTTP `/mcp`; OAuth discovery when deployed | Unverified | Private secure tunnel is only a development test path, never a public distribution endpoint. [Recipe](recipes/chatgpt-developer-mode.md) |
| ChatGPT published app | Stable HTTPS `/mcp`, discovery and approved review flow | Blocked | Requirements and publication not authorized or verified |
| OpenAI Responses API | Authenticated remote MCP | Unverified | [Recipe](recipes/openai-responses.md) |
| Claude API | Remote MCP connector, bearer/OAuth as officially supported | Unverified | [Recipe](recipes/claude-api.md) |
| Claude Desktop / Code | Local stdio; remote only where client documentation supports it | Unverified | Community stdio is the current Alpha transport |
| Gemini CLI | Local `mcpServers` or `httpUrl` where documented | Unverified | [Recipe](recipes/gemini-cli.md) |
| Gemini API / ADK | Official MCP adapter when available | Unverified | Requires an authorized spike and client-specific report |
| Gemini consumer web / mobile | No verified official path | Unverified | Do not imply support |
| Own Python agents | Python stdio SDK now; remote adapter later | Alpha local only | [`docs/sdk.md`](../sdk.md) |
| Own TypeScript agents | Transport-agnostic SDK scaffold | Experimental | [Recipe](recipes/own-agents.md) |
| Other MCP clients | Standard protocol | Compatible, untested | “Compatible” is not a tested claim |

Revalidate official client documentation at the start of every release; clients
and authorization requirements change. The canonical sources to check are
[OpenAI MCP concepts](https://developers.openai.com/plugins/concepts/mcp-server),
[OpenAI secure MCP tunnels](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels),
[Anthropic MCP connector](https://platform.claude.com/docs/en/agents-and-tools/mcp-connector),
and [Gemini CLI MCP guidance](https://codelabs.developers.google.com/gemini-cli-deep-dive).
