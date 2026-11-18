#!/usr/bin/env bash
set -euo pipefail

KEYS_FILE="secrets/.encryption_keys"
TMP_FILE="${KEYS_FILE}.tmp"

if [[ -s "$KEYS_FILE" ]]; then
    FIRST_LINE="$(awk 'NF && $1 !~ /^#/ {print; exit}' "$KEYS_FILE")"
    if [[ "$FIRST_LINE" =~ ^v([0-9]+): ]]; then
        NEXT_VERSION="v$((${BASH_REMATCH[1]} + 1))"
    else
        NEXT_VERSION="v2"
    fi
else
    NEXT_VERSION="v1"
fi

echo "Generating encryption key $NEXT_VERSION..."
NEW_KEY="$(openssl rand -base64 32)"

printf '%s:%s\n' "$NEXT_VERSION" "$NEW_KEY" > "$TMP_FILE"
cat "$KEYS_FILE" >> "$TMP_FILE" 2>/dev/null || true
mv "$TMP_FILE" "$KEYS_FILE"

echo "Done. $NEXT_VERSION is now the first line of $KEYS_FILE"
