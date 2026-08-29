# W01 — C01/C02 clean-SHA audit handoff

**Status:** BLOCKED — staging image publication is explicitly prohibited by the
delegation (`no push`). C01/C02 were not promoted and their checklist lines
remain unchanged.

## Context and ownership

- Worktree: `/Users/marcellojunqueirafranco/.codex/worktrees/688b/UMCP`
- Expected source branch: `codex/fix-pr-1` (this task worktree is detached but
  points at that branch)
- Initial observed SHA: `a9e7b5deefeb0f43799e95a09a263bea5a5757d6`
- Audit source SHA after the authorized verifier fix: `87e7b0a5fa55759bcf99fecd30250f4cb2b45519`
- Final local tree: clean
- Exclusive scope respected: only `scripts/verify_checksums.py` and this W01
  handoff were changed; C01/C02/containment reports and checklist lines were
  not changed.

## Current evidence

| Check | Result | Evidence |
| --- | --- | --- |
| Existing verifier before fix | FAIL | `ModuleNotFoundError: anyio` from package import |
| Stdlib-only verifier | PASS | `python3 -S scripts/verify_checksums.py` |
| Existing report checksums | PASS | C01, C02 and containment canonical/file hashes |
| Audit image build | PASS locally | Docker image built from SHA `87e7b0a…` |
| Local image ID | observed | `sha256:092bc562315f6d977f806a4ab842ee99765641cd79e44889dba15528d8ea40b6` |
| Registry publication | NOT-RUN | `docker push` was refused before egress because the delegation forbids push |
| Hosted C01/C02 rerun | NOT-RUN | Cannot reference the new image by registry digest without publication |
| Containment rerun | NOT-RUN | Same dependency on the new immutable registry image |

## Commands run

```text
python3 scripts/verify_checksums.py                  PASS
python3 -S scripts/verify_checksums.py               PASS
docker build --platform linux/amd64 .../umcp-audit:latest  PASS
```

The existing historical artifacts still report the prior audit source SHA and
remain useful only as historical evidence. They were not rewritten because no
new hosted run occurred.

## Provenance and safety

The intended hosted run remains restricted to the staging project, region,
service, migration job and disposable audit jobs named by the resumption
handoff. No production, external user, real credential, push, PR, tag, release
or C03 action was performed. No token, OAuth code, e-mail, connection string or
secret value was recorded.

## Required next action

An owner must explicitly resolve the conflict between the W01 requirement to
run a new immutable registry-backed audit image and the delegation's absolute
`no push` rule. Until that authority is supplied, do not use the old image as a
substitute, do not use an indirect Cloud Build path, and do not mark C01/C02
complete.
