#!/bin/bash
# dl_verified <url> <dest> <magic> - download with retry/backoff and content check.
# magic: "gzip" requires 1f 8b magic bytes; "digit" requires first char 0-9 (tsv).
# Fails loudly after 6 attempts instead of saving an error page.
set -euo pipefail
url=$1; dest=$2; magic=$3
ok() {
  [ -s "$dest" ] || return 1
  case "$magic" in
    gzip) [ "$(od -An -tx1 -N2 "$dest" | tr -d ' \n')" = "1f8b" ];;
    digit) head -c 1 "$dest" | grep -q '[0-9]';;
    *) return 0;;
  esac
}
for i in 1 2 3 4 5 6; do
  if ! ok; then
    curl -fSL --retry 3 --retry-all-errors --connect-timeout 20 -o "$dest" "$url" || true
  fi
  if ok; then echo "downloaded $dest ($(stat -c%s "$dest") bytes)"; exit 0; fi
  echo "download attempt $i for $dest failed content check; backing off" >&2
  sleep $((i * 20))
done
echo "FAILED to download $url after 6 attempts" >&2; exit 1
