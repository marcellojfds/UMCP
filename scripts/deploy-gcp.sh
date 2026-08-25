#!/usr/bin/env sh
set -eu

echo "H02 supplies local review controls only; provider deployment is blocked." >&2
echo "Required before any external action: recorded CP-1 and CP-3 approvals." >&2
exit 78
