# P00 — Productization baseline manifest

**Date:** 2026-08-21
**Working branch:** `terra-alpha-recovery`
**HEAD/base SHA:** `4947ebfb3789558892c242e0d7a8743256f3656d` (`feat: establish Open Memory Protocol alpha baseline`)
**Scope:** Wave 0, read-only baseline checks. No holdout access, staging,
commit, remote Git operation, dependency/model download, publication, or
secret rotation was performed.

## Baseline inventory

The primary worktree is intentionally dirty and must be preserved. At time of
inspection it contained 19 modified tracked paths and 64 untracked paths, in
addition to 170 paths tracked at `HEAD`. The untracked material includes the
semantic-runtime, migration, evaluation, report, documentation and handoff
evidence described by the proposed T04 manifest. No files were moved,
overwritten, deleted, staged or committed.

Two worktrees are registered:

| Worktree | Branch | HEAD | Status |
| --- | --- | --- | --- |
| `/Users/marcellojunqueirafranco/Documents/UMCP` | `terra-alpha-recovery` | `4947ebf` | primary, dirty; preserve |
| `/private/tmp/umcp-s08-semantic-embedding-selection` | `s08-semantic-embedding-selection` | `4947ebf` | preserved historical S08 evidence |

The current primary worktree is not a clean baseline SHA. Creating a clean
baseline requires the separately authorized, exact-path staging and local
commits described in T04 (or an alternative maintainer-approved preservation
plan). This document itself is a new untracked handoff and does not alter that
fact.

## Artifact integrity

All 14 `evals/reports/**/checksums.json` manifests were verified using the
JSON filename-to-SHA-256 mapping in each manifest. Every declared `report.json`
and `report.md` matched. The frozen retrieval-v0 dataset was not opened or
changed; no holdout was inspected or executed.

`git diff --check` completed with no output. `./scripts/scan-ci-safety` passed.
The safe local fast gate passed: Ruff reported no issues and pytest reported
`47 passed`; the only warning was the pre-existing Starlette/httpx deprecation
warning. A credential-shaped scan reported zero candidate paths and printed no
secret values.

`.gitignore` excludes `.env*`, virtual environments/caches, local databases,
exports, artifacts, `*.dump`, and other generated data. `git ls-files -o
--exclude-standard` contains no cache, model-weight, virtualenv, database dump,
or `/private/tmp` path. This confirms the current candidate inventory does not
include those classes; it is not permission to stage any path.

## Chronological reconciliation

1. **S07 (historical RC audit):** `NO-GO` for its then-unborn/dirty state;
   it correctly requires an immutable SHA, green checks, backup/restore/delete
   evidence, and an independent follow-up audit. It does not authorize Git or
   release operations.
2. **T03 (current E5 development promotion):** the frozen E5 configuration
   (`intfloat/e5-small-v2`, pinned revision, 384 dimensions, threshold `0.76`)
   is *development promotion eligible* only. Its harness and PostgreSQL/gateway
   evidence agree; the holdout remains prohibited and no threshold/model
   selection may be repeated retroactively.
3. **T04 (proposed commit manifest):** defines exact commit groups for the
   preserved local work, but expressly provides no authorization to stage,
   commit, push, create a PR, or use the holdout.
4. **GOAL-PROGRESS:** records the same base SHA, preserved local evidence and
   later E5 development equivalence. Its older S08 entries remain historical;
   the later T03 decision is the applicable development-promotion status.

There is no contradiction that upgrades the project to a release decision:
the current status is still non-release, with the holdout, remote CI, a clean
committed candidate, publication authorization, and independent S07-R2 audit
all separate gates.

## Outstanding authorizations

The following permissions remain required; none is inferred by this baseline:

1. Revoke/rotate the previously exposed OpenAI key and configure replacement
   secrets, if any. The compromised key was neither used nor printed.
2. Stage the exact T04 paths (without globs) and inspect each staged diff.
3. Create the proposed local commits and thereby establish a clean baseline
   SHA.
4. Create dedicated, isolated Terra and Luna worktrees/branches after the
   baseline is clean. Luna must not use this dirty primary worktree.
5. Download/install any additional dependency, model, audit tool, identity
   provider, KMS, queue, or infrastructure service.
6. Push, create/change remote branches, PRs, GitHub settings, tags, releases,
   packages, containers, sites, or other published resources.
7. Access or execute the sealed holdout (one separately authorized run only,
   after the required clean SHA and gates).
8. Contact external users or open a beta.

## P00 gate result

**BLOCKED, correctly:** integrity and safe local checks are green, but P00
cannot reach a clean SHA or enable productization implementation while the
required staging/commit and worktree authorizations are absent. No release-GO
claim is made.
