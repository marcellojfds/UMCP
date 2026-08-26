# H07 — image provenance ready (local-only)

## Scope and boundary

This handoff adds a fail-closed, locally inspectable promotion contract. It
does not build, inspect, publish, deploy, authenticate to, or modify any
external service. It does not change `H07-ENTRYPOINT-TRACE.md`.

The contract cannot prove a registry image's contents while offline. Instead,
it prevents Terraform configuration and the local deploy gate from accepting
an unpinned image or a source SHA that is absent, malformed, or different from
the checked-out source commit. Antigravity must retain the image-inspection
evidence that binds the supplied digest to that source commit.

## Delivered contract

- `ops/terraform/gcp/variables.tf` requires `image_digest` as an
  `@sha256:` reference and `image_source_sha` as a lowercase full 40-character
  Git SHA.
- `ops/terraform/gcp/guards.tf` includes both values in the fail-closed
  checkpoint guard; malformed or absent values prevent a valid configuration.
- `ops/terraform/gcp/cloud_run.tf` records the source SHA on the Cloud Run
  revision template label `source-sha`, providing a post-deploy audit handle.
- `scripts/deploy-gcp.sh` requires `IMAGE_DIGEST` and `IMAGE_SOURCE_SHA`, and
  rejects a SHA that is not exactly `git rev-parse HEAD`; after those local
  checks it still exits `78` and performs no provider action.
- `scripts/validate-gcp-local` asserts the complete contract structurally.

## Local validation

Run only from the candidate source checkout:

```sh
./scripts/validate-gcp-local
sh -n scripts/deploy-gcp.sh
IMAGE_DIGEST='registry.example/umcp@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa' \
IMAGE_SOURCE_SHA="$(git rev-parse HEAD)" \
  ./scripts/deploy-gcp.sh
```

The last command must exit `78` after validating the pair. It must exit `64`
when either value is missing or malformed and `65` when the SHA differs from
the checked-out commit. If Terraform is available, its offline formatting check
is also:

```sh
terraform fmt -check -recursive ops/terraform/gcp
```

No `terraform init`, `plan`, `apply`, registry access, or cloud command is a
validation step in this handoff.

## Antigravity promotion input

1. Check out the exact intended source commit. Obtain its lowercase full SHA
   with `git rev-parse HEAD`.
2. Build and inspect the candidate through its separately approved process,
   retaining evidence that the inspected image was built from that checkout
   and Dockerfile.
3. Resolve the immutable digest and pass the exact same pair everywhere:
   `IMAGE_DIGEST=<registry/repository@sha256:...>` and
   `IMAGE_SOURCE_SHA=<40-character checked-out SHA>` to the local gate; set
   Terraform `image_digest` and `image_source_sha` to those identical values.
4. Preserve the inspection record with the digest, SHA, Dockerfile revision,
   build identity/time, and CP-1/CP-3 decision record. Do not substitute tags,
   abbreviated SHAs, or a SHA from a different checkout.

## Rollback and post-deploy audit

Rollback is a separately approved promotion of a previously recorded
digest/SHA pair; never retag a mutable image. Before any rollback, re-run the
same local gate from the recorded SHA checkout. After an approved deployment,
compare the Cloud Run revision template label `source-sha` with the recorded
`image_source_sha`, compare the revision image to the recorded
`image_digest`, and attach that comparison to the promotion record. Any absent
or mismatched value is an audit failure and requires halting further promotion.
