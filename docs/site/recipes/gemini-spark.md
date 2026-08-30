# Gemini Spark custom-app recipe

**Status:** verified in the maintainer's private staging account on 2026-08-30.

1. Open Gemini **Settings → Personal Intelligence → Connected Apps**.
2. Add the UMCP `/mcp` URL as a custom app.
3. Complete UMCP Google OAuth with the same owner identity.
4. Switch to **Gemini Spark**.
5. Type `@` and select **Umcp Cloud** from the menu.
6. Ask for the saved preference and approve `memory.search`.

While the retrieval defect is open, a diagnostic prompt can request
`min_relevance: 0.0`. This is evidence of the defect, not the desired normal
workflow. Constrain Spark to UMCP if it tries unrelated Google apps.
