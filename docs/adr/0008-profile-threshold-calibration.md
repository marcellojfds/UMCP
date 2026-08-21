# ADR 0008 — Calibração de threshold por embedding profile

**Status:** calibration concluded; production-promotion validation preregistered
on 2026-08-20

## Contexto

O threshold público histórico de `0.78` foi definido para `hash/v1`.  Cosine
similarity não é comparável em escala absoluta entre espaços de embedding.  O
resultado em `0.78` permanece parte da evidência histórica, mas não decide por
si se E5 ou BGE falharam em ranking ou apenas em calibração operacional.

Os gates públicos permanecem imutáveis: precision@5 >= 0.80, intrusion@5 <=
0.10, abstention >= 0.90, lifecycle/isolation = 1.00, p95 < 2500 ms e o floor
de precision@5 >= 0.60 para cada `query_kind` positivo com pelo menos cinco
queries.  Nenhum conteúdo, label ou split do corpus será alterado.

## Protocolo congelado

- Escopo: exclusivamente episódios `development` 01--20; holdout não é
  selecionado, inferido, ranqueado, medido ou usado para selecionar threshold.
- Folds: cinco folds determinísticos, por episódio: o episódio numérico `n`
  pertence ao fold `(n - 1) mod 5`. Cada fold valida quatro episódios e calibra
  nos outros dezesseis.
- Grade: os 41 valores `0.50, 0.51, ..., 0.90`, inclusivos. A grade não será
  modificada depois de observar resultados.
- Em cada fold, um threshold só é elegível se o conjunto de calibração atender
  abstention >= 0.90, intrusion@5 <= 0.10, lifecycle/isolation = 1.00 e os
  floors de slices aplicáveis. Entre elegíveis, escolhe-se o de maior
  precision@5; empates escolhem o maior threshold e, persistindo, a ordem
  numérica estável.
- O threshold escolhido é então aplicado uma única vez ao fold de validação.
  Métricas finais são exclusivamente a agregação out-of-fold dessas cinco
  validações. Não existe promoção se algum fold não conseguir seleção válida.
- `0.78` é também reavaliado como baseline descritivo, sem afetar a seleção.

## Decisão

O candidato só é elegível para o caminho PostgreSQL/gateway se a agregação
out-of-fold passar todos os gates públicos. Os thresholds por fold não são uma
configuração de produção: se houver aprovação development-only, uma
configuração única deverá ser congelada em etapa posterior e revalidada antes
de solicitar autorização de holdout.

Todos os artifacts preservam apenas IDs, scores, parâmetros e checksums. Eles
não copiam texto do corpus e não sobrescrevem relatórios históricos.

## Promotion rule authorised by the maintainer

The maintainer has selected `intfloat/e5-small-v2` at revision
`ffb93f3bd4047442299a41ebb6fa998a38507c52` as the sole production-promotion
candidate. This is an operational-risk decision: E5 already has an offline
provider, migrations, re-embedding, cutover and rollback implementation and
tests. It is not a claim of statistical superiority to BGE; the BGE evidence
remains harness-only and unchanged.

The sole production threshold is the median of the five E5 thresholds selected
under the frozen protocol above: `median(0.76, 0.76, 0.76, 0.76, 0.77) =
0.76`. It is now frozen. No alternate threshold may be evaluated for this
promotion.

Before any new execution, the promotion configuration freezes: E5 ID and
revision, mean pooling, `query:`/`passage:` prefixes, dimension 384, threshold
0.76, candidate limit 50, result limit 5, the existing corpus/labels and the
unchanged public gates. Exactly one full development validation will run in
each of the corrected harness and the real PostgreSQL/repository/application/
gateway path. Both paths must meet every gate and agree on returned IDs for
the fixed development fixture; score values may differ only by `1e-6` rounding
at the application boundary. A failure is a promotion NO-GO and does not
authorize threshold adjustment, BGE promotion, a hybrid, model acquisition or
holdout.
