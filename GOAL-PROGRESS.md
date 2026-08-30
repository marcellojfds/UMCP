# UMCP current progress

**Updated:** 2026-08-30
**Canonical deployed source:** `1233b221fd89edb1691bd6bd09c2d21eee4822bf`

## Delivered

- hosted MCP over exact Streamable HTTP `/mcp`;
- Google OAuth with server-derived owner and tenant;
- ChatGPT memory capture in the private staging account;
- owner portal login and memory inspection;
- Gemini Spark custom app with all five UMCP actions synchronized; and
- exact cross-surface recall of the saved favorite-color preference.

## Active product milestone

Make cross-client recall work naturally without tool-parameter prompt
engineering.

Acceptance:

1. ChatGPT stores a synthetic durable preference.
2. Gemini Spark receives the plain-language prompt
   `@Umcp Cloud qual é a minha preferência?`.
3. UMCP returns the correct memory without the prompt mentioning
   `min_relevance`, `limit`, or a tool name.
4. An unrelated query still abstains.
5. Portal, OAuth, owner isolation, and revocation regressions remain green.

## Next

1. Calibrate retrieval per embedding profile.
2. Remove ChatGPT-specific provenance from generic capture.
3. Automate the two-surface staging acceptance journey.
4. Improve login/connection guidance and portal controls.
5. Verify one Claude surface only after P0 is stable.

See [Current state](docs/CURRENT_STATE.md) and [Roadmap](docs/roadmap.md).
