#!/usr/bin/env bash
# End-to-end smoke test against a running stack.
# Usage: scripts/smoke.sh [BASE_URL]   (default http://localhost:8000)
set -euo pipefail

BASE="${1:-http://localhost:8000}"
HERE="$(cd "$(dirname "$0")" && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

step() { printf '\n== %s\n' "$*"; }
fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }
expect() { grep -q -- "$2" <<<"$1" || fail "$3 (got: ${1:0:300})"; }
# upload DIR FILE OUTFILE -> prints HTTP status. cd + relative name keeps Windows curl happy.
upload() { (cd "$1" && curl -sS -o "$3" -w '%{http_code}' -F "files=@$2;type=application/pdf" "$BASE/api/documents"); }

step "health"
expect "$(curl -fsS "$BASE/api/health")" '"ok"' "health not ok"

step "upload sample.pdf"
code="$(upload "$HERE/fixtures" sample.pdf "$TMP/sample.json")"
[ "$code" = 200 ] || fail "sample upload returned HTTP $code"
expect "$(cat "$TMP/sample.json")" '"chunks"' "sample.pdf was not ingested"

step "upload 2 MB corrupt pdf (must reach backend and be reported, not 413)"
head -c 2000000 /dev/urandom > "$TMP/corrupt.pdf"
code="$(upload "$TMP" corrupt.pdf "$TMP/corrupt.json")"
[ "$code" = 200 ] || fail "corrupt upload returned HTTP $code"
expect "$(cat "$TMP/corrupt.json")" '"corrupt.pdf"' "corrupt.pdf not listed in errors"

step "upload 11 MB pdf (over the 10 MB limit)"
head -c 11000000 /dev/urandom > "$TMP/big.pdf"
code="$(upload "$TMP" big.pdf "$TMP/big.json")"
[ "$code" = 200 ] || fail "big upload returned HTTP $code"
expect "$(cat "$TMP/big.json")" 'File exceeds 10 MB limit' "size limit not enforced"

step "create chat"
chat="$(curl -fsS -X POST "$BASE/api/chats")"
id="$(sed -E 's/.*"id":"([^"]+)".*/\1/' <<<"$chat")"
[ -n "$id" ] || fail "no chat id in: $chat"
echo "chat id: $id"

step "stream an answer"
stream="$(curl -fsS -N -H 'Content-Type: application/json' \
  -d '{"content":"How many stripes complete a Zebra Protocol handshake?"}' \
  "$BASE/api/chats/$id/messages")"
expect "$stream" 'event: sources' "no sources event"
expect "$stream" 'event: token' "no token events"
expect "$stream" 'event: done' "no done event"
expect "$stream" 'sample.pdf' "sources do not cite sample.pdf"
printf '%s\n' "$stream" | sed -n 's/^data: {"text": "\(.*\)"}$/\1/p' | tr -d '\n'; echo

step "chat is listed and persisted"
expect "$(curl -fsS "$BASE/api/chats")" "$id" "chat not listed"
expect "$(curl -fsS "$BASE/api/chats/$id")" '"assistant"' "assistant message not saved"

step "delete chat"
code="$(curl -sS -o /dev/null -w '%{http_code}' -X DELETE "$BASE/api/chats/$id")"
[ "$code" = 204 ] || fail "delete returned HTTP $code"

printf '\nSMOKE OK\n'
