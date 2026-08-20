# Disposable PostgreSQL gate

This environment is only for the Core/Postgres integration gate. It uses
PostgreSQL 16 with pgvector, binds only to loopback port `55433`, and stores
the database on a container tmpfs. No project or host data volume is mounted.

Start and run the complete Lane A gate from the repository root:

```bash
./scripts/gate-postgres
```

The script runs migration zero → head, the required integration suite in gate
mode, downgrade/upgrade on the disposable database, and removes the container.
An external disposable database can still be used directly with
`OMP_TEST_DATABASE_URL`; SQLite and PostgreSQL without the `vector` extension
are not supported evidence.
