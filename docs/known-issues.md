# Known issues and release blockers

These are intentionally visible in the `0.1.0a1` release-candidate
documentation.

## Evidence blockers

- The corrected S08 handoff is present and is an explicit NO-GO: E5
  `precision@5=0.756` on development with the frozen `0.78` threshold. The
  holdout remains sealed and no semantic quality or Gate B GO may be claimed.
- The separately authorized BGE S08-R3 experiment is also an explicit NO-GO:
  `precision@5=0.000` on development with normalized CLS pooling and the
  model-card query instruction. BGE was not integrated into runtime or
  PostgreSQL/gateway.
- S05-R2, holdout, clean committed SHA, remote CI/settings, and final S07-R2
  evidence remain release gates; local package/SBOM/vulnerability gates now
  pass in disposable environments.
- The constraints file is verified only for Python 3.11 on macOS arm64; other
  platforms and a clean build environment remain unverified.
- GitHub Private Vulnerability Reporting was selected as the channel, but this
  local session cannot enable or verify repository settings.

## Product limitations

- `owner_id` is client-provided and trusted in local stdio composition. It is
  logical scoping, not authentication or authorization; hosted multi-tenant
  use is unsupported.
- Memory content, provenance, evidence, relations, exports, backups, and
  embeddings are sensitive. The operator can read database/process/files;
  embeddings are not anonymous. Default exports omit vectors but are not safe
  to share by default.
- The project does not provide E2EE, zero knowledge, hosted auth, tenant
  isolation, or a claim of scale. The file-backed demo is not production
  evidence.
- MCP transport support is stdio only. HTTP health/readiness is not an MCP
  endpoint, and other language SDKs are not provided.

## Next decision points

The maintainer must review S04/S05 evidence when available, complete S07's
clean-room audit, verify the security channel, and decide whether this remains
an engineering preview or is eligible for a GitHub Release. A new semantic
experiment must be authorized separately before any holdout execution. No
publication is authorized.
