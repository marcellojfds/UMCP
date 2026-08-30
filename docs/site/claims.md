# Public claim gate

Use these labels in landing copy, demos, README text, and social metadata.

| Claim | Current status | Allowed wording |
| --- | --- | --- |
| User-owned portable memory | Private-MVP evidence | “One signed-in owner accessed the same UMCP memory from ChatGPT, Gemini Spark, and the UMCP portal in private staging.” |
| Google OAuth login | Implemented and privately verified | Scope to UMCP staging and the allowlisted account |
| Server-derived owner isolation | Implemented and tested | Do not imply independent production audit or operator blindness |
| Encrypted in transit/at rest | Architecture and staging controls exist | Do not use as a blanket marketing claim until release-SHA evidence is reconciled |
| End-to-end encrypted / zero knowledge | Prohibited | The server decrypts memory for retrieval |
| Works everywhere | Prohibited | List only individually verified surfaces |
| Production-ready | Prohibited | Current environment is private staging |
| Public beta | Prohibited | Enrollment, policy, support, and readiness gates are not complete |

Never include real memory content, emails, OAuth codes, bearer/refresh tokens,
cookies, database URLs, or secret values in public evidence.
