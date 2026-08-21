# T01 — Retrieval diagnostic and threshold-calibration result

**Status:** development-only evidence; no candidate frozen; release remains **NO-GO**.

## Scope and preservation

- Evaluated only the 40 development queries from episodes 01--20. The report
  field is `holdout_executed: false`; no holdout query was embedded, ranked,
  measured or emitted.
- The historical reports remain unchanged. The first recovery run
  `20260820T201046Z-4947ebfb3789-semantic-development` is preserved but is
  superseded for decision purposes because it exposed a harness/gateway result
  ordering mismatch. The corrected artifact is
  [`20260820T201231Z-4947ebfb3789-semantic-development`](../../../evals/reports/20260820T201231Z-4947ebfb3789-semantic-development/).
- The corrected `report.json` SHA-256 is
  `8cb6ce83d7d0ed284a7c0dda69805121740c7cde38e80fa87c15b9a8eb8ba35e`.
  It stores identifiers, scores, filters-as-booleans and metrics only; it does
  not copy corpus text.

## Protocol audit

| Check | Evidence | Result |
| --- | --- | --- |
| precision denominator, empty-positive and intrusion denominator | hand-calculated unit examples in `tests/evals/test_metrics.py` | conforms to EVALS_PLAN |
| filters before candidate ranking | `rank_before_threshold` and PostgreSQL repository apply owner/state/space/type before ranking | conforms by code review |
| E5 encoding equivalence | harness and runtime both use local pinned revision, `query:`/`passage:`, attention-mask mean pooling, L2 normalisation, dimension 384 | conforms by code review |
| BGE encoding | harness uses the authorized query instruction and normalized CLS pooling; BGE has no runtime provider | harness-only, no production claim |
| score/order equivalence | recovery found that the harness initially retained cosine order while gateway reranks threshold-passing items by similarity, importance and confidence; corrected and regression-tested | corrected before decisive rerun |
| pgvector path | repository uses `1 - cosine_distance`, profile/source-version filters and candidate limit before service threshold | code-equivalent pending disposable PostgreSQL parity test |
| sealed boundary | current JSONL corpus combines development and holdout, so structural validation parses the combined artifact before split filtering | governance limitation; no holdout result was used |

The regression `test_thresholded_harness_result_uses_gateway_score_tie_break`
now prevents the recovered order mismatch. Local `gate-fast`, eval tests and
CI-safety scan pass after the correction.

## Threshold-independent development ranking

| Profile | Recall@5 | MRR | nDCG@5 | Positive candidate coverage | Historical 0.78 precision@5 | Classification |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| E5 small v2 | 1.000 | 1.000 | 0.833 | 1.000 | 0.756 | `CALIBRATION_NO-GO` at 0.78 |
| BGE small en v1.5 | 1.000 | 0.964 | 0.813 | 1.000 | 0.000 | `CALIBRATION_NO-GO` at 0.78 |

Both profiles place relevant results in the candidate ranking. The fixed
historical threshold suppresses E5 marginally and BGE almost completely; this
is not evidence of ranking failure.

## Pre-registered calibration result

ADR 0008 was written before the sweep. Its fixed 0.50--0.90 grid and five
episode-grouped folds selected thresholds only from the corresponding sixteen
calibration episodes, then measured the four unseen validation episodes. The
out-of-fold metrics are:

| Profile | Fold thresholds | Precision@5 | Intrusion@5 | Abstention | Lifecycle/isolation | p95 ms | OOF result |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| E5 small v2 | 0.76, 0.76, 0.76, 0.76, 0.77 | 0.827 | 0.000 | 1.000 | 1.000 | 19.926 | passes gates |
| BGE small en v1.5 | 0.54, 0.51, 0.56, 0.58, 0.58 | 0.804 | 0.000 | 0.917 | 1.000 | 19.156 | passes gates |

No gate, corpus byte, label or split changed. The slice floor was part of each
fold's eligibility check.

## Recovery decision

There is no `RANKING_NO-GO`, and the pre-registered per-profile calibration
passes development for both profiles. Therefore T4 hybrid is not triggered and
was not run. No model was acquired.

The protocol deliberately did **not** pre-register a way to derive one
production threshold from the fold thresholds, nor a cross-profile tie-break.
Choosing E5 or BGE now from these results would select on measurements that
were not specified for that decision. Consequently no profile, config or code
has been frozen, no PostgreSQL gateway run has been requested, and no holdout
authorization is being sought. The next required decision is a narrowly
scoped, pre-registered promotion/selection protocol (or an explicit choice of
one profile and a fixed threshold rule) before further development evaluation.
