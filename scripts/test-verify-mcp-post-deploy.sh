#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd); fake=$(mktemp -d "${TMPDIR:-/tmp}/umcp-fake-curl.XXXXXX"); trap 'rm -rf "$fake"' EXIT HUP INT TERM
cat > "$fake/curl" <<'EOF'
#!/bin/sh
headers= body=
while [ "$#" -gt 0 ]; do case "$1" in --dump-header) headers=$2; shift 2;; --output) body=$2; shift 2;; *) shift;; esac; done
printf 'HTTP/2 200\r\nX-UMCP-Image-Digest: sha256:abc123\r\nX-UMCP-Image-Source-SHA: 0123456789abcdef0123456789abcdef01234567\r\n\r\n' > "$headers"; : > "$body"
EOF
chmod +x "$fake/curl"
out=$(CURL_BIN="$fake/curl" "$root/scripts/verify-mcp-post-deploy.sh" --endpoint https://synthetic.example/mcp --allowed-host synthetic.example --expected-image-digest sha256:abc123 --expected-source-sha 0123456789abcdef0123456789abcdef01234567)
[ "$out" = "PASS endpoint=https://synthetic.example/mcp image_digest=sha256:abc123 source_sha=0123456789abcdef0123456789abcdef01234567" ]
if CURL_BIN="$fake/curl" "$root/scripts/verify-mcp-post-deploy.sh" --endpoint http://synthetic.example/mcp --allowed-host synthetic.example --expected-image-digest sha256:abc123 --expected-source-sha 0123456789abcdef0123456789abcdef01234567 >/dev/null 2>&1; then exit 1; fi
echo "PASS offline verifier validation (fake curl; no network)"
