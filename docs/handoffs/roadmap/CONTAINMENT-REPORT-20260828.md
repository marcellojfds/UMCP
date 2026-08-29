# Relatório de Contenção de Credenciais e Tenancy em Staging

- **Data:** 2026-08-29T14:10:27.700645Z
- **Status de Contenção:** **PASS**
- **Base URL Staging:** `https://umcp-cloud-staging-yqjlathj7q-uc.a.run.app`
- **Audit Source SHA:** `72b9fad4d9ed6b54f44150d19fc3d3edef67e1ab`
- **Server Source SHA:** `367cd365df43f9282f5155394cd39275169bf8f2`
- **Server Image Digest:** `sha256:764263db4907ffbbbd50e77ab7d12e8d88cde2b5990a9879a40ddbd0976e4f1d`
- **Server Active Revision:** `umcp-cloud-staging-00018-f78`
- **Audit Image Digest:** `sha256:c39b3d02785b0a4f817da4074136b4d662c49085499e6cebbf8a69b96ccbedea`
- **Report ID:** `containment-72b9fad4d9ed`
- **Canonical JSON Artifact:** [`CONTAINMENT-REPORT-20260828.json`](./CONTAINMENT-REPORT-20260828.json)
- **Checksum do Payload Canônico (SHA-256):** `sha256:35fbdf2f12b53af8fc699fd013d55804c137c00eb2964790d7ca7b95c3ba8911`
- **Checksum do Arquivo JSON (SHA-256):** `sha256:f9a4d9cad9474e1ece0d9b6a8197f47765e839b0adabe4579e754db713ebb339`

---

## 1. Métricas de Contenção

- **active_tokens:** `0`
- **active_codes:** `0`
- **active_test_tenants:** `0`

---

## 2. Garantias Operacionais

- Zero tokens em logs, stdout, stderr, arquivos ou argumentos.
- Ciclo de vida efêmero e estritamente restrito à memória de execução VPC.
- Purga confirmada com contagens exatas no Cloud SQL.
