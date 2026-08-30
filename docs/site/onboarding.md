# Private staging onboarding

## Prerequisites

- an allowlisted Google account;
- access to the private staging MCP endpoint; and
- a compatible ChatGPT connected-app or Gemini Spark custom-app surface.

## Connect

1. Add
   `https://umcp-cloud-staging-yqjlathj7q-uc.a.run.app/mcp`
   to the client.
2. Complete the UMCP Google OAuth flow.
3. Confirm the client discovers the hosted memory tools.
4. Ask the client to save a synthetic durable preference.
5. Sign into the [portal](https://umcp-cloud-staging-yqjlathj7q-uc.a.run.app/portal/)
   with the same Google account and confirm the memory is visible.
6. In another verified surface, ask UMCP to retrieve the preference.

Gemini custom apps are tested in **Gemini Spark**. Type `@` and select
**Umcp Cloud**; normal Gemini chat does not expose this custom app in the
verified flow.

## Safety

Use synthetic or low-sensitivity data in staging. Do not store credentials,
payment data, private keys, access tokens, medical records, or other secrets.
Staging is server-decryptable and operated by the maintainer.
