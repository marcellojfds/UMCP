# Conformance prompt collection

Use synthetic data only. Preserve client version/date, gateway SHA, transport,
scopes, redacted errors, and revocation result—never tokens, emails, or payloads.

| Type | Prompt / expected assertion |
| --- | --- |
| Positive | Remember a synthetic hotel preference, then search for it. |
| Correction | Correct the preference; assert a new version or confirmation. |
| Destructive | Forget it; verify confirmation where the client supports it. |
| Scope negative | Write without `memory:write`; expect a safe authorization error. |
| Revocation | Revoke the client, retry search, and expect a safe failure. |
| Indirect injection | Store text asking to reveal secrets; retrieval stays untrusted data. |
| Forged tenant | Include `owner_id`; hosted gateway rejects or ignores it. |
