# Installation and connection

UMCP currently has two distinct paths: the private hosted staging MVP and the
local Community development environment.

## Private hosted staging

MCP endpoint:

```text
https://umcp-cloud-staging-yqjlathj7q-uc.a.run.app/mcp
```

The endpoint advertises its OAuth metadata. A compatible client should open
the UMCP/Google authorization flow automatically. Staging accepts only the
allowlisted maintainer identity.

### ChatGPT

1. Open ChatGPT's connected-app/developer connector settings.
2. Add the exact MCP endpoint above.
3. Complete the UMCP Google OAuth flow with the allowlisted account.
4. Confirm the tools include `memory.capture` and `memory.search`.
5. Ask explicitly to remember a durable, non-sensitive preference.
6. Verify it at the [UMCP portal](https://umcp-cloud-staging-yqjlathj7q-uc.a.run.app/portal/).

The exact ChatGPT UI and availability can change; this is a private staging
recipe, not a published-app installation guide.

### Claude Code

Claude Code is the selected Claude surface for the private staging acceptance.
The hosted service uses Streamable HTTP plus OAuth/PKCE; do not configure the
local `python -m omp.server` stdio process when you intend to use the hosted
vault.

1. Use a current Claude Code release with remote MCP OAuth support.
2. Add UMCP as a user-level server with the registered public client and fixed
   loopback callback:

   ```bash
   claude mcp add --transport http --scope user \
     --client-id umcp-claude-code --callback-port 17171 \
     umcp https://umcp-cloud-staging-yqjlathj7q-uc.a.run.app/mcp
   ```

3. Start Claude Code, enter `/mcp`, select `umcp`, and complete Google sign-in
   with an allowlisted account. Newer releases also support:

   ```bash
   claude mcp login umcp
   ```

4. Verify the result:

   ```bash
   claude mcp list
   ```

   The `umcp` server must report `Connected` before it can expose memory tools.
5. Ask Claude explicitly to search UMCP or save a durable, non-sensitive memory.

This recipe does not claim equivalent verification for Claude Desktop or the
Claude API; those are separate surfaces with different setup and token flows.

### Gemini Spark

1. In Gemini, open **Settings → Personal Intelligence → Connected Apps**.
2. Under custom apps for Spark, add the exact MCP endpoint above.
3. If Gemini requests advanced OAuth fields, use the registered public client
   ID supplied by the UMCP operator and leave the client secret blank. Do not
   invent or share a secret for a PKCE public client.
4. Complete UMCP Google OAuth with the same Google identity used by the portal
   and other clients.
5. Switch from normal Gemini chat to **Gemini Spark**.
6. Type `@`, then select **Umcp Cloud** from the menu.
7. Approve the read/write tool action when Gemini asks.

Diagnostic recall prompt while the retrieval issue remains open:

```text
Use only the Umcp Cloud memory.search tool. Search for my preference with
limit 10 and min_relevance 0.0. Do not search other connected apps.
```

## Owner portal

Open:

```text
https://umcp-cloud-staging-yqjlathj7q-uc.a.run.app/portal/
```

Select **Sign in**, use the same Google account, and open **Memories**. The
portal session and MCP clients resolve to the same server-derived owner only
when the verified Google subject is the same.

## Local development setup

Requirements:

- Python 3.11;
- Docker; and
- PostgreSQL 16 with pgvector for the supported database gate.

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
docker compose -f ops/postgres/compose.yaml up -d --wait
export OMP_DATABASE_URL='postgresql+asyncpg://omp_test:omp_test@127.0.0.1:55433/omp_test'
OMP_DATABASE_URL="$OMP_DATABASE_URL" alembic upgrade head
./scripts/gate-fast
./scripts/gate-postgres
```

Stop the disposable database with:

```bash
docker compose -f ops/postgres/compose.yaml down
```

The optional file-backed mode is a deterministic demo fixture, not hosted or
multi-user evidence.
