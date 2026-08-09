#!/usr/bin/env bash
# Fleet update helper — push the current product build to every ACTIVE
# cloud studio (DEPLOYMENT.md "Then update the tenant fleet"). Run AFTER a
# release is live on main and the storefront is serving the new rev.
#
# The admin token is a secret: it NEVER lives in the repo or in a command
# line that could land in shell history / a transcript. This script reads
# it, in order, from:
#   1. $ADMIN_EXPORT_TOKEN in the environment, or
#   2. the file $SCREENBOARD_ADMIN_TOKEN_FILE
#      (default: ~/.screenboard_admin_token), which is outside the repo.
# Put your token there once, in your OWN terminal, e.g.:
#   printf '%s' 'PASTE_TOKEN_HERE' > ~/.screenboard_admin_token
#   chmod 600 ~/.screenboard_admin_token
#
# Usage:
#   scripts/update_tenants.sh            # trigger the fleet update
#   scripts/update_tenants.sh --status   # read-only: list per-studio deploys
#
# Sent as `Authorization: Bearer` (preferred — a ?token= query lands in
# access logs). The token is never printed.
set -euo pipefail

BASE_URL="${SCREENBOARD_BASE_URL:-https://www.screenboardstudio.com}"
TOKEN_FILE="${SCREENBOARD_ADMIN_TOKEN_FILE:-$HOME/.screenboard_admin_token}"

token="${ADMIN_EXPORT_TOKEN:-}"
if [ -z "$token" ] && [ -f "$TOKEN_FILE" ]; then
  token="$(tr -d '[:space:]' < "$TOKEN_FILE")"
fi
if [ -z "$token" ]; then
  echo "error: no admin token. Set \$ADMIN_EXPORT_TOKEN or write it to $TOKEN_FILE" >&2
  exit 1
fi

path="/admin/tenants/update"
[ "${1:-}" = "--status" ] && path="$path?status=1"

# -sS: quiet but still show errors; capture the HTTP code on its own line.
resp="$(curl -sS -w '\n%{http_code}' --max-time 60 \
  -H "Authorization: Bearer ${token}" "${BASE_URL}${path}")"
code="${resp##*$'\n'}"
body="${resp%$'\n'*}"

echo "$body"
if [ "$code" != "200" ]; then
  echo "error: HTTP $code from ${path%%\?*}" >&2
  exit 1
fi
