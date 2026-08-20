# Executar o MCP Alpha local

O caminho suportado usa PostgreSQL + pgvector. O backend file-backed abaixo é
somente um harness explicitamente solicitado para smoke/contrato.

## Smoke rápido

```bash
OMP_DATABASE_URL='postgresql+asyncpg://...' alembic upgrade head
OMP_DATABASE_URL='postgresql+asyncpg://...' PYTHONPATH=src python -m omp.cli eval smoke --json
PYTHONPATH=src python examples/e2e_two_clients.py
PYTHONPATH=src pytest -q tests/contract tests/e2e
```

## Gate rápido sem PostgreSQL

Para validar qualidade estática e os testes unitários/contratuais sem iniciar
PostgreSQL, execute na raiz do repositório:

```bash
./scripts/gate-fast
```

O comando roda `ruff check .`, `mypy src` e
`pytest -q tests/unit tests/contract`. Integração PostgreSQL e E2E permanecem
fora deste gate; use `./scripts/gate-postgres` quando o banco descartável
estiver disponível.

## Servidor stdio

```bash
OMP_DATABASE_URL='postgresql+asyncpg://...' PYTHONPATH=src python -m omp.server
```

O processo fala MCP stdio por meio do SDK oficial. Não envie conteúdo real para
logs/fixtures. O processo falha se o Postgres não estiver pronto e não ativa
um backend alternativo.

## Demo explícito

```bash
PYTHONPATH=src python -m omp.server --demo-backend --data-file /tmp/omp-memory.json
PYTHONPATH=src python -m omp.cli --demo-backend --data-file /tmp/omp-memory.json status --json
```

O modo demo é rotulado e não representa produção, auth hosted ou E2EE.

## Export/import PostgreSQL

O export é owner-scoped e não inclui embeddings por default. O import efetivo
usa os ports administrativos reais do application service; o modo demo deve
ser selecionado explicitamente e não conta como evidência do Gate B.

```bash
OMP_DATABASE_URL='postgresql+asyncpg://...' PYTHONPATH=src \
  python -m omp.cli --json export /tmp/omp-export.json --owner-id owner-a
PYTHONPATH=src python -m omp.cli --json import --dry-run /tmp/omp-export.json
OMP_DATABASE_URL='postgresql+asyncpg://...' PYTHONPATH=src \
  python -m omp.cli --json import /tmp/omp-export.json
```

`dry-run` apenas valida o pacote e não muta o banco. O import retorna erro
estável em pacote inválido ou divergente e repetir o mesmo pacote não duplica
memórias.

## Health/readiness

O app FastAPI opcional expõe somente `/healthz` (liveness) e `/readyz`
(Postgres/pgvector/migration readiness). Nenhum deles retorna configuração,
secrets, owner, IDs ou conteúdo. O HTTP não é transporte MCP suportado.

## Diagnóstico

Use `omp status --json` e `omp eval smoke --json`. Os logs do adapter só
contêm request ID, tool, status, duração em bucket, erro estável e contagem de
resultados. Query, conteúdo, provenance, embedding e raw IDs não são campos
permitidos.

## Exit codes do CLI

`0` indica sucesso; `1` erro interno; `2` validação/arquivo inválido; `3`
memória não encontrada; `4` conflito de versão; `5` operação proibida; `6`
rate limit; `7` dependência indisponível (incluindo Postgres ausente). Com
`--json`, o objeto de erro mantém `error.code`, `error.message` genérica e
`error.retryable`.

## Backup, restore e deletion after restore

Estes procedimentos são para PostgreSQL local/self-hosted. Execute somente com
dados sintéticos no gate e guarde backups fora do checkout, com permissões
restritas. Backup é conteúdo sensível: não o anexe a issues, CI ou artifacts.
É necessário usar `pg_dump`/`pg_restore` da mesma major do servidor ou mais
nova; um client mais antigo falha de modo seguro.

### Backup lógico

```bash
umask 077
OMP_DATABASE_URL='postgresql://...' ./scripts/backup-postgres /secure/omp-$(date +%F).dump
pg_restore --list /secure/omp-$(date +%F).dump >/dev/null
```

O script usa formato custom do `pg_dump`, não imprime a URL e cria o arquivo
com `umask 077`. A responsabilidade por criptografia em repouso e armazenamento
seguro é do operador.

### Restore em alvo descartável

Nunca use `restore-postgres` contra o banco de produção ativo: ele usa
`--clean --if-exists`. Crie um banco descartável, aplique o restore e valide
o estado antes de trocar qualquer tráfego.

```bash
OMP_DATABASE_URL='postgresql://.../omp_restore_gate' \
  ./scripts/restore-postgres /secure/omp-2026-08-20.dump
OMP_DATABASE_URL='postgresql+asyncpg://.../omp_restore_gate' \
  python -m alembic current
```

### Forget após restore

O ledger de forget é metadata-only e é restaurado junto com o banco. A janela
de retenção escolhida para o Alpha é: backups permanecem somente pelo prazo
operacional definido pelo operador; qualquer backup restaurado deve ter as
solicitações de deleção reaplicadas antes de ser usado. Como o Alpha ainda não
tem uma fila externa de solicitações/tombstones, o operador deve fornecer uma
lista de IDs e owners a reaplicar e registrar essa execução fora do conteúdo.

```bash
OMP_DATABASE_URL='postgresql+asyncpg://.../omp_restore_gate' PYTHONPATH=src \
  python -m omp.cli --json memory forget --owner-id synthetic-owner \
  --id 00000000-0000-0000-0000-000000000000 --idempotency-key restore-delete-001
```

Verifique que memória, versões, embedding e relações foram removidos. Exports
prévios não são revogados: localize e descarte-os conforme a política do
operador. Esta limitação impede qualquer claim de apagamento imediato de
backups ou exports.

### Retenção e descarte

- O aplicativo não retém conteúdo em logs por design; configure e aplique
  retenção no coletor do operador.
- Não suba `.dump`, `.omp`, exports, stderr, traces ou banco como artifacts de
  CI. O único artifact CI permitido é a distribuição Python, retida por 1 dia.
- Ao expirar um backup, apague-o usando o mecanismo recuperável/política de
  storage aprovada pelo operador e registre apenas data, operador e identificador
  do backup — nunca conteúdo.

## Outage e recuperação

1. Confirme liveness e readiness: `/healthz` deve responder `ok`; `/readyz`
   deve retornar 503 durante indisponibilidade de Postgres, sem URL, SQL ou
   stack trace.
2. Não troque para `--demo-backend`. Demo é somente um harness explicitamente
   iniciado; o processo padrão falha fechado se Postgres/migration/pgvector
   não estiverem prontos.
3. Recupere Postgres/pgvector, execute `alembic current`, e somente então
   reinicie `python -m omp.server`.
4. Uma requisição excedendo `timeout_ms` retorna `dependency_unavailable`;
   o adapter não faz retry automático. Clientes podem repetir apenas operações
   seguras com idempotency key e backoff próprio.
5. Para shutdown, envie SIGTERM e aguarde o processo encerrar; o runtime fecha
   o engine no `finally`. Não interrompa uma migração no meio: use o gate ou
   uma manutenção coordenada.
