#!/usr/bin/env sh
set -eu

image_digest=${IMAGE_DIGEST:-}
image_source_sha=${IMAGE_SOURCE_SHA:-}

if ! printf '%s\n' "$image_digest" | grep -Eq '^.+@sha256:[0-9a-f]{64}$'; then
  echo "Refusing promotion: IMAGE_DIGEST must be an immutable image reference with a sha256 digest." >&2
  exit 64
fi

if ! printf '%s\n' "$image_source_sha" | grep -Eq '^[0-9a-f]{40}$'; then
  echo "Refusing promotion: IMAGE_SOURCE_SHA must be a lowercase, full 40-character Git commit SHA." >&2
  exit 64
fi

checked_out_sha=$(git rev-parse --verify HEAD)
if [ "$image_source_sha" != "$checked_out_sha" ]; then
  echo "Refusing promotion: IMAGE_SOURCE_SHA does not match the checked-out source commit." >&2
  exit 65
fi

echo "H02 supplies local review controls only; provider deployment is blocked." >&2
echo "Required before any external action: recorded CP-1 and CP-3 approvals." >&2
exit 78
