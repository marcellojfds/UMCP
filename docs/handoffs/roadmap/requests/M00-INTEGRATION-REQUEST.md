# M00 integration request — Verification handoff ready

Status: `waiting-for-integration-owner`

The Verification lane has published:

- `roadmap/luna-verification:docs/handoffs/roadmap/M00-VERIFICATION-DONE.md`
- tested executable SHA `2c305ed1d339bec1252a087df60d38e2741235c7`
- evidence and checksums under `docs/handoffs/roadmap/evidence/`

The Core and Experience refs expose their M00 handoffs:

- `roadmap/luna-core:docs/handoffs/roadmap/M00-CORE-DONE.md`
- `roadmap/luna-experience:docs/handoffs/roadmap/M00-EXPERIENCE-DONE.md`

Current ref tips inspected by Verification:

- `roadmap/luna-core` → `164d84b77e74e37d63f42dfc99ae26df1f83765c`
- `roadmap/luna-experience` → `64a9181f870e01d01f6dbb3229cb32086cd0f46`
- `roadmap/luna-verification` → `4d22842fd3392e4bace4e430bdb6245722086e19`

The controlled integration ref still lacks
`docs/handoffs/roadmap/M00-INTEGRATED.md`. The independent readiness proof is:

```sh
scripts/assert-m00-branch-handoffs
```

It returns `WAITING`/exit 2 until the integration owner merges the applicable
handoffs, reruns the integrated acceptance/demo and current gates, and writes
`M00-INTEGRATED.md`. Verification does not merge, edit another lane, or issue
a release GO.

The stale coordination checkpoint is recorded in
[`M00-INTEGRATION-001.md`](../findings/M00-INTEGRATION-001.md); it must not be
used as integrated acceptance evidence.
