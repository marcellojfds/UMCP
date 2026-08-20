# Handoff R01 — contratos do core prontos

## Resultado

Os commands, ports e erros internos de update/forget estão estáveis para o
terminal MCP consumir. A camada de transporte deve apenas propagar a chave de
idempotência para o application service.

## Assinaturas

```python
MemoryApplicationService.update(UpdateMemoryCommand) -> Memory
MemoryApplicationService.forget(ForgetMemoryCommand) -> ForgetMemoryResult

UpdateMemoryCommand(..., idempotency_key: str | None = None)
ForgetMemoryCommand(owner_id: str, memory_id: UUID,
                    idempotency_key: str | None = None)

IdempotencyRepository.claim(
    owner_id: str,
    operation_type: IdempotencyOperationType,
    idempotency_key: str,
    fingerprint: str,
) -> IdempotencyClaim
IdempotencyRepository.complete(
    claim: IdempotencyClaim,
    memory_id: UUID | None,
    result_version: int | None,
    result_status: str,
) -> None
```

`operation_type` é `update` ou `forget`. A chave é isolada por owner e por
tipo de operação. O fingerprint é SHA-256 do JSON canônico definido no ADR
0003; a chave não participa do próprio fingerprint.

## Erros estáveis

Além dos erros já publicados, o core expõe `IdempotencyConflictError` com
`code="idempotency_conflict"` e `IdempotencyInProgressError` com
`code="idempotency_in_progress"`. O adapter MCP deve mapear ambos sem incluir
payload sensível.

## Replay

Update com a mesma key e fingerprint replaya o snapshot da versão registrada e
nunca incrementa novamente. Key reutilizada com fingerprint diferente falha.
Replay de update depois de forget pode retornar `not_found`. Forget retorna
`forgotten=false` em replay e em chamadas posteriores já ausentes. Chaves de
update e forget com o mesmo texto são independentes.

## Storage

A migration head é `0002_idempotency_operations`. Ela adiciona o ledger
metadata-only e foreign keys compostas owner+memory para impedir relações
cross-owner no banco. Claim, mutação e complete acontecem na mesma Unit of
Work; rollback remove claim incompleto.

## Ação requerida do consumidor

O gateway MCP deve preencher `idempotency_key` em `UpdateMemoryCommand` e
`ForgetMemoryCommand`. Nenhuma alteração de MCP foi feita neste terminal.
