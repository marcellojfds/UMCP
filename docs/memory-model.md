# OMP memory model v0

Este documento descreve o contrato interno do core MVP 0. Ele é independente
de MCP, HTTP e SQL; adapters de transporte devem mapear seus schemas para os
commands de `omp.application`.

## Aggregate

Uma `Memory` possui `id` UUID opaco, `owner_id` obrigatório, `content` textual,
`type`, `importance`, `confidence`, `state`, `version`, timestamps, `space`
opcional, proveniência, descriptor de embedding e idempotency key opcional.
`importance` e `confidence` são floats em `[0, 1]`. Timestamps precisam de
timezone. Conteúdo vazio, owner ausente, versão não positiva e dimensão inválida
falham com `validation_error`.

Tipos v0: `fact`, `preference`, `decision`, `insight`, `hypothesis`, `lesson`,
`goal`, `project_context`, `concept`, `relationship`, `open_question`.

States v0 persistidos: `active`, `superseded`, `contradicted`, `archived`.
`forgotten` é o resultado de uma exclusão, não uma linha com conteúdo.

## Lifecycle

- `active -> active`, `superseded`, `contradicted` ou `archived`;
- `contradicted -> active` quando há nova evidência;
- `archived -> active` por restauração explícita;
- `superseded` não volta a `active` no MVP.

Transições para `superseded` ou `contradicted` exigem `related_memory_id` e o
application service registra uma relação correspondente quando solicitado.
Toda alteração incrementa `version`; o caller deve enviar
`expected_version` e conflitos não fazem merge silencioso.

## Proveniência e histórico

`Provenance` registra `source_type`, `captured_at`, `source_id` opcional,
`source_model` opcional e evidências opcionais. O histórico é composto por
snapshots versionados e é apagado no forget. Evidência não é interpretada pelo
domínio nem usada para inventar conteúdo.

## Relações

Relações são arestas relacionais do mesmo owner: `supports`, `contradicts`,
`derived_from`, `related_to`, `supersedes` e `applies_to`. Self-relations são
inválidas. Não há graph database no MVP.

## Forget e idempotência

Forget exige owner e memory id, remove conteúdo corrente, snapshots, vetor e
relações incidentes numa única transação. Se a memória já não existe para o
owner, retorna `forgotten=false`. A idempotency key é única por `(owner_id,
key)`; replay do mesmo payload retorna a memória original e payload diferente
retorna `idempotency_conflict`.

Update e forget aceitam `idempotency_key` independente da write key. O ledger
de operações usa `(owner_id, operation_type, idempotency_key)`, com `update` e
`forget` como tipos distintos. Update registra um fingerprint SHA-256 e a
versão produzida: replay exato retorna o snapshot dessa versão sem novo
incremento; fingerprint divergente retorna `idempotency_conflict`; replay após
forget pode retornar `not_found`. Forget retorna `forgotten=true` na primeira
remoção e `forgotten=false` nas repetições, inclusive com outra key. O ledger
metadata-only sobrevive ao cascade de forget e nunca armazena conteúdo,
query, proveniência, evidência ou embedding.

## Retrieval baseline

`search` gera um embedding no profile configurado, busca candidatos dentro do
owner e profile, aplica filtros e considera apenas `active` por default. O
similarity normalizado precisa alcançar o threshold; importance/confidence
apenas ordenam candidatos já semanticamente relevantes. O score é:

```text
0.75 * similarity + 0.15 * importance + 0.10 * confidence
```

Empates usam similarity e UUID como tie-break determinístico. Uma consulta
negativa retorna lista vazia. `reason_retrieved` enumera apenas sinais públicos
determinísticos, sem conteúdo adicional ou chain-of-thought.
