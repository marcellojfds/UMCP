# ADR 0005 — Export/import administrativo no core PostgreSQL

## Status

Aceito para R09 do Gate B.

## Contexto

O harness file-backed já possuía export/import, mas o caminho suportado do
Alpha é PostgreSQL. A Lane MCP precisa de um contrato administrativo que não
abra o repository diretamente, preserve dados de uma instância e possa ser
reexecutado sem duplicação.

## Decisão

`MemoryApplicationService` expõe:

```python
async def export_memories(
    *, owner_id: str, include_embeddings: bool = False
) -> tuple[MemoryExportRecord, ...]

async def import_memories(
    *, owner_id: str, records: Sequence[MemoryImportRecord]
) -> ImportResult
```

Os DTOs carregam a memória corrente, snapshots completos, relações incidentes,
um vetor opcional e o digest da write idempotency key quando a memória possui
uma. O digest não é conteúdo e permite preservar replay de write; o ledger
`idempotency_operations` de update/forget não é exportado.

## Política de dados

- Export é sempre limitado a um `owner_id`; não existe export global no port.
- Memórias, provenance, lifecycle, histórico e relações são exportados.
- Vetores ficam excluídos por default. Com `include_embeddings=True`, o vetor
  e seu profile são carregados para reuso direto.
- Sem vetor, import gera um novo embedding somente se o provider configurado
  tiver exatamente o profile/dimensão/metric da memória.
- O ledger de operações não é exportado, importado ou recriado; retries de
  update/forget não são reativados por um import.
- Forget segue o ledger local de destino e não cria tombstones de export.

## Validação e transação

O application service materializa a sequência, valida IDs únicos, owner,
enum/timestamps/invariantes, sequência completa de versões, fingerprints,
vetores e owners das relações. Também valida endpoints externos antes de
mutar. Depois compara registros existentes completos; payload divergente gera
`ImportConflictError` (`code="import_conflict"`). Nenhum registro é gravado
antes de todas essas validações terminarem.

O repository grava todas as memórias, vetores, snapshots e relações na mesma
Unit of Work. IDs estáveis e `ON CONFLICT DO NOTHING` tornam reimport idêntico
um replay; uma falha faz rollback de todo o pacote. Relações são inseridas
somente depois de todas as memórias para respeitar as FKs owner+endpoint.

## Alternativas rejeitadas

- Importar diretamente nas tabelas a partir do MCP: quebraria a separação de
  camadas e duplicaria regras.
- Exportar o ledger: permitiria reativar operações antigas e misturaria
  retenção operacional com backup de memória.
- Incluir vetores sempre: aumentaria o payload sensível e impediria
  re-embedding controlado no destino.
- Aceitar owner ausente ou endpoints cross-owner: criaria um export global e
  violaria o isolamento obrigatório.
- Aplicar registro a registro: permitiria estado parcial quando um registro
  posterior fosse inválido.
