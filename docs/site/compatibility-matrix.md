# Client compatibility matrix

**Last reviewed:** 2026-08-30

| Surface | Status | Notes |
| --- | --- | --- |
| ChatGPT connected app | Verified in private staging | OAuth and memory capture exercised; [recipe](recipes/chatgpt-developer-mode.md) |
| Gemini Spark custom app | Verified in private staging | Tool sync and exact recall exercised; retrieval-threshold workaround remains; [recipe](recipes/gemini-spark.md) |
| Gemini normal chat | Not available in verified path | Switch to Spark |
| UMCP portal | Verified in private staging | Same Google owner can inspect memories |
| Claude | Not verified | [planned acceptance recipe](recipes/claude-api.md) |
| OpenAI Responses API | Not verified separately | [planned acceptance recipe](recipes/openai-responses.md) |
| Gemini CLI/API/ADK | Not verified separately | Consumer Spark evidence does not transfer to these surfaces |
| Own Python agents | Implemented/tested locally | Python SDK and controlled-agent harness |
| Own TypeScript agents | Experimental | Transport-agnostic scaffold only |

“Verified” is limited to the maintainer account, date, staging endpoint, and
source SHA recorded in [Current state](../CURRENT_STATE.md).
