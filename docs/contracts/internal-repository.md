# Contrato interno — repository/unit of work v0

`MemoryRepository` e `IdempotencyRepository` são Protocols async em
`omp.application.ports`. Toda
operação recebe `owner_id` explicitamente; não existe método de leitura global.
O port de memória cobre get/version replay, idempotency lookup de write, create,
compare-and-swap update, vector candidate search, forget, relations e history.
O port de idempotência faz `claim`/`complete` para update e forget usando a
chave composta `(owner_id, operation_type, idempotency_key)`. Claim e mutação
ocorrem na mesma Unit of Work; rollback remove claim incompleto.

`UnitOfWork` abre uma transação com `async with`, expõe `memories` e faz commit
somente quando não há exceção. O adapter PostgreSQL implementa esse contrato
com SQLAlchemy Core/asyncpg; `InMemoryUnitOfWorkFactory` é o fake oficial para
testes de MCP/application.

`MemoryAdminRepository` é o port administrativo assíncrono exposto como
`UnitOfWork.admin`. `export_memories` e `export_memory` sempre recebem
`owner_id`; `import_memories` recebe DTOs previamente validados pelo service.
O adapter PostgreSQL grava memórias, vetores, snapshots e relações na mesma
transação, usa IDs estáveis e trata reimport idêntico como replay. O ledger de
idempotência de update/forget não é parte do export/import.

O repository retorna apenas candidatos cujo owner/profile/filter foram validados
antes do ranking. O ranking, threshold e reason determinístico pertencem ao
application service. Vetores nunca aparecem no domínio ou em logs.
