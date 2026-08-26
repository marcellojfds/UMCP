#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
sha=0123456789abcdef0123456789abcdef01234567
run() { "$root/scripts/preflight-h07-audit.sh" --endpoint https://synthetic.example/mcp --project umcp-staging --allowed-project umcp-staging --region southamerica-east1 --allowed-region southamerica-east1 --service mcp --revision rev-synthetic --image-digest sha256:abc123 --source-sha "$sha" --identity-ref identity-synthetic --connection-ref connection-synthetic --mode read-only "$@"; }
run >/dev/null
for bad in http://synthetic.example/mcp https://synthetic.example/wrong; do
  if run --endpoint "$bad" >/dev/null 2>&1; then exit 1; fi
done
if run --project other-project >/dev/null 2>&1; then exit 1; fi
if run --mode read-write >/dev/null 2>&1; then exit 1; fi
if run --identity-ref bearer-token-synthetic >/dev/null 2>&1; then exit 1; fi
echo "PASS offline H07 audit preflight tests (no network, GCP, auth, secrets, or real data)"
