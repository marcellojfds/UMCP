# T02 — staging promotion gate

**Status:** complete / staging promotion verified.

## Candidate

- source SHA: `6f41101b33a6d75430ad9cceba3c3c11a1c53c03`
- immutable image: `us-central1-docker.pkg.dev/umcp-mcp-staging-20260825/umcp-docker-repo/umcp@sha256:90c0e8128c99e44fb7bc08ab237f9296aa742361bc9c7c780dac7ec2bf575692`

## Acceptance

1. deploy the exact digest as a no-traffic staging revision with
   `OMP_IMAGE_SOURCE_SHA` equal to the source SHA;
2. prove the revision responds at `/login` with the hosted Google handoff and
   provenance headers matching the SHA/digest;
3. only then move 100% staging traffic to that exact revision;
4. on any failure, preserve or restore 100% traffic to the prior revision.

This package does not run client OAuth, create a connection, or claim T00's
cross-platform acceptance.

## Result

- Cloud Build: `5235feab-5470-4b6b-bbf9-066f20120bac` built the candidate
  from the clean source SHA and returned the immutable digest above.
- Canary revision: `umcp-cloud-staging-00022-cab`, tagged `t02-login`, was
  created with no traffic and verified at `/login` before cutover.
- Staging traffic: 100% moved to `umcp-cloud-staging-00022-cab` only after
  the canary returned HTTP 200, `Continue with Google`, no-store and CSP
  headers, and matching `X-UMCP-Image-Digest` / `X-UMCP-Image-Source-SHA`.
- The previous 100% revision was `umcp-cloud-staging-00019-bhg`. It remains
  the rollback target; no database migration was performed.

## Current gates

| Gate | Result | Freshness |
| --- | --- | --- |
| T01 local contract and authority tests | pass | current on source SHA |
| canary `/login` + provenance headers | pass | current on immutable digest |
| 100% staging `/login` + provenance headers | pass | current on immutable digest |
| Google OAuth / three independent clients | not-run | T03–T07 |
