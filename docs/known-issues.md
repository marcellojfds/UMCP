# Known issues and release blockers

These are intentionally visible in the `0.1.0a1` release-candidate
documentation.

## Evidence blockers

- No S04 handoff or retrieval report is present in this checkout. The frozen
  `retrieval-v0` corpus exists, but `hash/v1` quality, slices, and p50/p95 have
  not been measured here. Do not claim semantic retrieval quality or Gate B
  `GO`.
- No S05 handoff is present. Backup/restore/delete-retention, outage, and
  operational policy evidence are not available here; the privacy baseline
  still calls backup restore and retention blockers for a public Alpha.
- Dependency ranges are declared but no complete lock/constraints artifact is
  present. Reproducible release builds remain S07 work.
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
an engineering preview or is eligible for a GitHub Release. No publication is
authorized by S06.
