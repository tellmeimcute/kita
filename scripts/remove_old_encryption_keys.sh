#!/usr/bin/env bash
set -euo pipefail

KEYS_FILE="secrets/.encryption_keys"
TMP_FILE="${KEYS_FILE}.tmp"

ACTIVE_KEY="$(awk 'NF && $1 !~ /^#/ {print; exit}' "$KEYS_FILE" 2>/dev/null || true)"
if [[ -z "$ACTIVE_KEY" ]]; then
    echo "No active key found. Nothing to do."
    exit 0
fi

printf '%s\n' "$ACTIVE_KEY" > "$TMP_FILE"
mv "$TMP_FILE" "$KEYS_FILE"

echo "Done. Only the first key is left in $KEYS_FILE"
