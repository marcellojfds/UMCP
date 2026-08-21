# ADR 0007 — Runtime local e re-embedding semântico

**Status:** desenho implementado experimentalmente; não aprovado para RC
enquanto a seleção S08 corrigida permanecer NO-GO.

## Decisões

- O provider semântico é local-only, carrega `transformers`/`torch` somente no
  extra `semantic`, exige diretório de pesos previamente provisionado e valida
  a revisão Hugging Face antes do startup.
- O provider usa mean pooling, normalização L2 e prefixos configuráveis
  separados para `query:` e `passage:`. Não há fallback remoto ou fallback
  silencioso para hash.
- `hash/v1` permanece em `memory_embeddings` com `vector(64)`. O profile
  semântico usa `memory_embeddings_semantic` com `vector(384)` e nunca é
  comparado com a tabela de outra dimensão.
- Cada vetor semântico registra `source_version`; buscas e cutover excluem
  vetores obsoletos após uma escrita concorrente.
- O re-embedding é owner-scoped, paginado por UUID, idempotente por chave
  `(memory_id, profile_id, profile_version)`, e só altera o profile corrente no
  cutover após cobertura completa.
- Downgrade de `0003_semantic_embedding_profile` recusa descartar linhas
  semânticas não vazias. O rollback operacional é troca de configuração para
  hash/v1 ou restore verificado; não há downgrade destrutivo em dados reais.

## Protocolo operacional

1. Fazer backup verificado e restore smoke em banco separado antes de dados
   persistentes.
2. Executar dry-run por owner e depois batches retomáveis com `resume_after`.
3. Verificar `eligible == covered`, ausência de falhas/stale e lifecycle antes
   do cutover.
4. Alternar o profile por configuração; manter os dois perfis durante a
   janela de rollback.
5. Reaplicar forget/tombstones após qualquer restore.

## Limitação atual

No protocolo S08 corrigido, `intfloat/e5-small-v2` atingiu `precision@5=0.756`
no development, abaixo do gate `0.800`. Logo este ADR descreve um caminho
seguro de implementação, mas não aprova qualidade semântica nem holdout.
