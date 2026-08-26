#!/bin/sh
set -eu
usage() { echo "usage: $0 --endpoint https://host/mcp --allowed-host host --expected-image-digest sha256:<hex> --expected-source-sha <40-64 lowercase hex>" >&2; exit 64; }
endpoint= allowed_hosts= expected_digest= expected_sha=
while [ "$#" -gt 0 ]; do
  case "$1" in
    --endpoint) [ "$#" -ge 2 ] || usage; endpoint=$2; shift 2 ;;
    --allowed-host) [ "$#" -ge 2 ] || usage; allowed_hosts=$2; shift 2 ;;
    --expected-image-digest) [ "$#" -ge 2 ] || usage; expected_digest=$2; shift 2 ;;
    --expected-source-sha) [ "$#" -ge 2 ] || usage; expected_sha=$2; shift 2 ;;
    *) usage ;;
  esac
done
[ -n "$endpoint" ] && [ -n "$allowed_hosts" ] && [ -n "$expected_digest" ] && [ -n "$expected_sha" ] || usage
case "$endpoint" in https://*) ;; *) echo "FAIL: endpoint must use https://" >&2; exit 1;; esac
case "$endpoint" in *\?*|*\#*) echo "FAIL: endpoint must not contain query or fragment" >&2; exit 1;; esac
authority=${endpoint#https://}; host=${authority%%/*}; [ "$host" != "$authority" ] || { echo "FAIL: endpoint path must be exactly /mcp" >&2; exit 1; }
[ "/${authority#*/}" = /mcp ] || { echo "FAIL: endpoint path must be exactly /mcp" >&2; exit 1; }
case ",$allowed_hosts," in *",$host,"*) ;; *) echo "FAIL: host is not in the explicit allowlist" >&2; exit 1;; esac
case "$expected_digest" in sha256:*) digest_hex=${expected_digest#sha256:};; *) echo "FAIL: expected image digest must be sha256:<hex>" >&2; exit 1;; esac
case "$digest_hex" in ""|*[!a-f0-9]*) echo "FAIL: expected image digest must be sha256:<hex>" >&2; exit 1;; esac
case "$expected_sha" in *[!a-f0-9]*) echo "FAIL: expected source SHA must be lowercase hex" >&2; exit 1;; esac
sha_len=$(printf %s "$expected_sha" | wc -c | tr -d ' '); [ "$sha_len" -ge 40 ] && [ "$sha_len" -le 64 ] || { echo "FAIL: expected source SHA must be 40-64 chars" >&2; exit 1; }
curl_bin=${CURL_BIN:-curl}; tmp=${TMPDIR:-/tmp}/umcp-mcp-verify.$$; trap 'rm -f "$tmp.headers" "$tmp.body"' EXIT HUP INT TERM
set +e
"$curl_bin" --silent --show-error --fail --proto '=https' --tlsv1.2 --max-redirs 0 --dump-header "$tmp.headers" --output "$tmp.body" "$endpoint"
status=$?
set -e
[ "$status" -eq 0 ] || { echo "FAIL: HTTPS request failed or redirected (curl exit $status)" >&2; exit 1; }
awk 'BEGIN{IGNORECASE=1} /^HTTP\// {if ($2 ~ /^3/) bad=1} END{exit bad}' "$tmp.headers" || { echo "FAIL: redirect response detected" >&2; exit 1; }
actual_digest=$(awk 'BEGIN{IGNORECASE=1} /^X-UMCP-Image-Digest:/ {sub(/^[^:]*:[[:space:]]*/,""); gsub(/[[:space:]]/,""); print; exit}' "$tmp.headers")
actual_sha=$(awk 'BEGIN{IGNORECASE=1} /^X-UMCP-Image-Source-SHA:/ {sub(/^[^:]*:[[:space:]]*/,""); gsub(/[[:space:]]/,""); print; exit}' "$tmp.headers")
[ "$actual_digest" = "$expected_digest" ] || { echo "FAIL: image digest mismatch or missing" >&2; exit 1; }
[ "$actual_sha" = "$expected_sha" ] || { echo "FAIL: source SHA mismatch or missing" >&2; exit 1; }
printf 'PASS endpoint=%s image_digest=%s source_sha=%s\n' "$endpoint" "$expected_digest" "$expected_sha"
