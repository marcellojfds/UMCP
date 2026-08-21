# M00 integration request — Verification handoff ready

Status: `waiting-for-integration-owner`

The Verification lane has published:

- `roadmap/luna-verification:docs/handoffs/roadmap/M00-VERIFICATION-DONE.md`
- tested executable SHA `2c305ed1d339bec1252a087df60d38e2741235c7`
- evidence and checksums under `docs/handoffs/roadmap/evidence/`

The Core and Experience refs expose their M00 handoffs:

- `roadmap/luna-core:docs/handoffs/roadmap/M00-CORE-DONE.md`
- `roadmap/luna-experience:docs/handoffs/roadmap/M00-EXPERIENCE-DONE.md`

The controlled integration ref still lacks
`docs/handoffs/roadmap/M00-INTEGRATED.md`. The independent readiness proof is:

```sh
scripts/assert-m00-branch-handoffs
```

It returns `WAITING`/exit 2 until the integration owner merges the applicable
handoffs, reruns the integrated acceptance/demo and current gates, and writes
`M00-INTEGRATED.md`. Verification does not merge, edit another lane, or issue
a release GO.
