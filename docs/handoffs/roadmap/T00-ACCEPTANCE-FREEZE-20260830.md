# T00 — acceptance freeze for real cross-platform staging

**Status:** frozen / not-run.  This package does not claim a product pass.

## Capability under test

ChatGPT, Claude, and Gemini independently complete Google OAuth authorization
code + PKCE S256 against the hosted UMCP staging page.  They resolve to one
stable owner/vault while retaining three distinct, independently revocable
connections and access-token families.

## Acceptance command

```text
python3 scripts/acceptance-cross-platform-staging --evidence-dir <redacted-evidence-dir>
```

The command accepts only three redacted client reports (`chatgpt.json`,
`claude.json`, `gemini.json`). It fails unless every report proves:

- hosted login and Google OAuth/PKCE;
- a separate connection and distinct access-token digest;
- one identity-subject and vault digest shared by all three;
- the same memory is created, read by ID, and semantically recalled by all
  clients;
- owner/tenant forgery is rejected and per-client revocation is verified.

It intentionally cannot pass from a fixture, health check, discovery,
`tools/list`, a shared token, or synthetic personas.

## Current evidence and rollback

At the frozen base `1895ca274a241428fde42b26758fbbe548288f69`, the deployed
staging digest is `sha256:764263db4907ffbbbd50e77ab7d12e8d88cde2b5990a9879a40ddbd0976e4f1d`.
Read-only probes on 2026-08-30 found `GET /` and `GET /login` return 404, so
the hosted login prerequisite is **not met**. No OAuth state, token, connection
or memory was created. Rollback for later promotion is routing traffic back to
the prior immutable digest after revoking the three test connections.

## Next package

T01 must serve the web/login surface from the Cloud Run artifact, preserve the
OAuth server as the sole authority for owner/tenant, and pass local negative
tests before a clean-SHA/digest staging promotion is considered.
