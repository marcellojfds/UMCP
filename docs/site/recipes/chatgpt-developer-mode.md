# ChatGPT connected-app recipe

**Status:** verified in the maintainer's private staging account on 2026-08-30.

1. Add the hosted endpoint:
   `https://umcp-cloud-staging-yqjlathj7q-uc.a.run.app/mcp`.
2. Complete UMCP Google OAuth with the allowlisted account.
3. Confirm `memory.capture` and `memory.search` are present.
4. Ask ChatGPT explicitly to remember a concise, non-sensitive preference.
5. Verify the memory in the UMCP portal.
6. Retrieve it from another verified surface.

Record exact UI/client date and deployed source SHA for every rerun. ChatGPT
may choose whether to call a tool; an explicit remember request is the
deterministic acceptance prompt.
