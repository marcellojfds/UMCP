# ADR 0003 — Idempotência de operações de update e forget

## Status

Aceito para R00–R04 do Alpha v0. A decisão é aditiva para o contrato interno;
o contrato MCP deve apenas propagar `idempotency_key` já existente em update e
forget.

## Contexto

O write já usa uma chave única por `(owner_id, idempotency_key)` na linha da
memória. Update e forget recebiam a chave no contrato MCP, mas a descartavam
antes do application service. Em PostgreSQL isso permitia que retries de uma
operação concluída aplicassem a mutação novamente. O ledger precisa sobreviver
ao forget, sem transformar uma tabela de operações em cópia de conteúdo
sensível.

## Semântica

As operações são identificadas por:

```text
(owner_id, operation_type, idempotency_key)
```

`operation_type` é `update` ou `forget`; chaves iguais de tipos diferentes são
independentes e owners nunca compartilham chaves.

- **Write:** preserva a semântica v0 existente: a key/fingerprint ficam na
  memória criada, replay igual retorna `created=false`, payload divergente
  retorna `idempotency_conflict`. Forget remove essa associação junto com a
  memória, portanto a mesma write key pode ser reutilizada depois de forget.
- **Update:** o fingerprint inclui memória alvo, `expected_version`, todos os
  campos do patch, relações de supersede/contradiction e `change_reason`, mas
  nunca a idempotency key. O primeiro claim e o compare-and-swap, snapshot,
  embedding e conclusão do ledger ocorrem na mesma transação. Replay concluído
  com fingerprint igual não executa mutação e retorna o snapshot da versão
  registrada; se a memória já foi esquecida, retorna `not_found`. A mesma key
  com fingerprint diferente retorna `idempotency_conflict`.
- **Forget:** o fingerprint inclui apenas o owner e a memória alvo. A primeira
  operação que remove algo retorna `forgotten`; chamadas posteriores, inclusive
  replay da mesma key, retornam `already_absent`. Uma key diferente também não
  pode recriar efeito. O ledger de forget fica sem FK para a memória e sobrevive
  ao cascade para preservar essa semântica.

## Fingerprint canônico

O fingerprint é SHA-256 do JSON UTF-8 canônico, com `sort_keys=true`,
`separators=(",", ":")` e valores enum serializados por seus valores string.
Timestamps são ISO-8601 em UTC; listas de evidence preservam ordem. O digest é
o único payload da operação persistido no ledger. Conteúdo pode contribuir para
o digest de update, mas nunca é persistido no ledger nem aparece em logs.

## Ledger, estados e retenção

`idempotency_operations` contém somente:

- `owner_id`, `operation_type`, `idempotency_key`;
- `fingerprint` SHA-256;
- `status` (`in_progress` ou `completed`);
- `memory_id`, `result_version` e `result_status` mínimos para reconstruir o
  resultado sem guardar conteúdo;
- `claimed_at` e `completed_at`.

A chave primária é composta por owner, tipo e key; há índice por owner/tipo.
Uma linha é inserida como `in_progress` dentro da mesma transação que fará a
mutação e só passa a `completed` depois de memória, histórico, vetor e relações
terem sido gravados. Rollback remove claims incompletos. O ledger não tem
expiração automática no MVP 0: ele é metadata-only e retenção indefinida evita
que uma limpeza reative uma mutação após retry tardio. Uma futura retenção/GC
exige ADR e janela de replay explícita.

## Concorrência

O claim usa insert concorrente com unique constraint e leitura `FOR UPDATE`.
Uma corrida com a mesma operação espera a transação vencedora; após o commit,
enxerga `completed` e faz replay sem incremento adicional. Operações distintas
continuam sujeitas ao `expected_version`/compare-and-swap: somente uma
atualização com a mesma versão esperada vence.

## Dados proibidos

O ledger não armazena content, query, provenance, evidence, embedding/vector,
resposta completa, prompt, stack trace, segredo ou owner bruto em logs. O
`owner_id` é necessário como chave relacional do ledger e deve ser redigido em
telemetria; o banco deve ser tratado como sensível.

## Migration e rollback

Como o alpha ainda não possui dados oficiais, a migration `0002` adiciona a
tabela sem reescrever `0001`. Downgrade em banco descartável remove apenas o
ledger. Em banco com dados, a operação suportada é forward migration; não se
remove o ledger sem decisão de retenção.

## Alternativas rejeitadas

- **Guardar o payload completo no ledger:** facilita replay, mas viola
  minimização e aumenta o impacto de dump/log/backup.
- **Reusar `memories.idempotency_key` para update/forget:** não diferencia
  operação, é apagado no forget e não representa versões/replays.
- **Tombstone por memória com conteúdo:** preservaria dados contra a intenção
  de forget e confundiria lifecycle com idempotência.
- **Lock distribuído ou Redis:** adicionaria outra persistência e não tornaria
  a mutação banco+ledger atômica.
- **Retornar sempre a memória corrente em replay:** depois de outro update o
  resultado não seria semanticamente equivalente ao primeiro resultado.
