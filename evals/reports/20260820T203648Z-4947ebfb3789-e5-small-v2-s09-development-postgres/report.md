# E5 promotion — PostgreSQL development validation

Decision: **NO-GO**

Only `development` was selected; `holdout_executed` is `false`.

The disposable PostgreSQL 16.15 / pgvector path reached migration head
`0004_semantic_source_version`, then failed on the first fixture write. The
semantic repository insert omitted required `source_version`; therefore no
search, query metric or threshold adjustment occurred.

This is an implementation failure, not a ranking or calibration result. The
frozen E5 promotion configuration remains unchanged at threshold `0.76`.
