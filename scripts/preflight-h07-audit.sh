#!/bin/sh
set -eu

usage() {
  echo "usage: $0 --endpoint https://host/mcp --project PROJECT --allowed-project PROJECT --region REGION --allowed-region REGION --service SERVICE --revision REVISION --image-digest sha256:HEX --source-sha HEX --identity-ref REF --connection-ref REF --mode read-only" >&2
  exit 64
}
fail() { echo "FAIL: $1" >&2; exit 1; }

endpoint=project=allowed_project=region=allowed_region=service=revision=digest=source_sha=identity_ref=connection_ref=mode=
while [ "$#" -gt 0 ]; do
  case "$1" in
    --endpoint|--project|--allowed-project|--region|--allowed-region|--service|--revision|--image-digest|--source-sha|--identity-ref|--connection-ref|--mode)
      [ "$#" -ge 2 ] || usage
      key=${1#--}; key=$(printf '%s' "$key" | tr '-' '_')
      [ "$key" = image_digest ] && key=digest
      eval "$key=\$2"; shift 2 ;;
    *) usage ;;
  esac
done

[ -n "$endpoint" ] && [ -n "$project" ] && [ -n "$allowed_project" ] && [ -n "$region" ] &&
[ -n "$allowed_region" ] && [ -n "$service" ] && [ -n "$revision" ] && [ -n "$digest" ] &&
[ -n "$source_sha" ] && [ -n "$identity_ref" ] && [ -n "$connection_ref" ] && [ -n "$mode" ] || usage

all_input="$endpoint $project $allowed_project $region $allowed_region $service $revision $digest $source_sha $identity_ref $connection_ref $mode"
case "$all_input" in
  *[Ss][Ee][Cc][Rr][Ee][Tt]*|*[Tt][Oo][Kk][Ee][Nn]*|*[Pp][Aa][Ss][Ss][Ww][Oo][Rr][Dd]*|*[Bb][Ee][Aa][Rr][Ee][Rr]*|*[Aa][Pp][Ii]_[Kk][Ee][Yy]*|*[Aa][Pp][Ii]-[Kk][Ee][Yy]*) fail "secret or token-like input is forbidden" ;;
esac
case "$endpoint" in
  https://*/*) : ;;
  *) fail "endpoint must use HTTPS" ;;
esac
authority=${endpoint#https://}; host=${authority%%/*}; path=/${authority#*/}
[ "$host" != "$authority" ] && [ "$path" = /mcp ] || fail "endpoint must be exactly https://host/mcp"
[ "$project" = "$allowed_project" ] || fail "project is outside the approved scope"
[ "$region" = "$allowed_region" ] || fail "region is outside the approved scope"
[ "$mode" = read-only ] || fail "mode must be read-only"
case "$digest" in sha256:[a-f0-9]*) : ;; *) fail "image digest must be sha256:<lowercase hex>" ;; esac
digest_hex=${digest#sha256:}; case "$digest_hex" in *[!a-f0-9]*) fail "image digest must be sha256:<lowercase hex>" ;; esac
case "$source_sha" in *[!a-f0-9]*) fail "source SHA must be lowercase hex" ;; esac
sha_len=$(printf %s "$source_sha" | wc -c | tr -d ' ')
[ "$sha_len" -ge 40 ] && [ "$sha_len" -le 64 ] || fail "source SHA must be 40-64 chars"
for value in "$project" "$allowed_project" "$region" "$allowed_region" "$service" "$revision" "$identity_ref" "$connection_ref"; do
  case "$value" in *[!ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._:/-]*) fail "metadata contains unsupported characters" ;; esac
done
printf '%s\n' "PASS H07 audit preflight: explicit HTTPS endpoint, approved scope, provenance, synthetic refs, read-only mode"
