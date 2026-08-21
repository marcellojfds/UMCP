# PostgreSQL/migrations evidence

- SHA tested: `45ca25c15fedfd383eb96f8a04141fbe2423d3d1`
- Disposable runtime: PostgreSQL `16.15`, pgvector `0.8.6`.
- Migration path: `base → 0001 → 0002 → 0003 → 0004 → 0005 → 0006 → 0007_tenant_fks`.
- Integration/E2E result: `19 passed`.
- Downgrade/re-upgrade result: returned to `0007_tenant_fks`.
- Cleanup note: the integration suite may leave the disposable database at
  `base`; the Verification-owned gate handles this explicitly.
- Data boundary: disposable synthetic database only; no persistent database or
  real data used.
