# Claude Code OAuth acceptance — 2026-09-02

## Result

Claude Code can register and authenticate to the hosted UMCP MCP endpoint in
private staging. Claude Code 2.1.236 completed the UMCP Google OAuth flow and
reported the `umcp` server as `Connected`.

This is MCP transport and OAuth acceptance, not yet full model-driven tool
lifecycle acceptance. The tested Anthropic account does not have Claude Pro or
Max and no Anthropic API key with available credits is configured. Claude Code
therefore stops at Anthropic model authentication before it can ask UMCP to
write or search a memory.

## Configuration exercised

```bash
claude mcp add --transport http --scope user \
  --client-id umcp-claude-code --callback-port 17171 \
  umcp https://umcp-cloud-staging-yqjlathj7q-uc.a.run.app/mcp
claude mcp login umcp
claude mcp list
```

The UMCP OAuth client is registered with the fixed loopback callback
`http://localhost:17171/callback`. The hosted redirect validator accepts
`localhost`, `127.0.0.1`, and `::1` loopback callbacks while continuing to
reject non-loopback insecure HTTP redirect URIs.

## Evidence

- Claude Code version: `2.1.236`.
- Remote MCP transport: Streamable HTTP at the canonical `/mcp` endpoint.
- UMCP authorization: completed through the configured Google-backed OAuth
  authorization-code flow with PKCE.
- Client status after authorization: `Connected`.
- Unauthenticated `/mcp` response: HTTP 401 with the expected protected-resource
  metadata challenge.
- Authorization-server metadata: HTTP 200.
- Portal onboarding: exact add/login/list instructions, staging allowlist note,
  and Claude Pro/Max or Anthropic API-key prerequisite are published.

No email address, OAuth token, authorization code, client secret, or browser
session value is recorded in this report.

## Remaining acceptance step

After an eligible Anthropic account or API key is available, run a
model-initiated `memory.write`, `memory.search`, `memory.update`, and
`memory.forget` lifecycle, verify owner isolation in the portal, and append the
redacted results here. Until then, UMCP must not claim complete Claude
model/tool lifecycle acceptance.

## Deployed artifact

- Revision: `umcp-cloud-staging-claude-final5`
- Source: `05b4a8eac282721eb4a7de5ecd511ce8e618a37c`
- Image: `sha256:c4467b47e88329081303978d3ff6f22f2edd8f096d711c6c2756d604ec0a3c45`
- Traffic after validation: 100%
