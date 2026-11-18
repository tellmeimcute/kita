#!/usr/bin/env bash
set -euo pipefail

openssl rand -hex 32 > secrets/.redis_password
printf 'user default on >%s ~* &* +@all\n' "$(cat secrets/.redis_password)" > secrets/.redis_acl

echo "Done. secrets/.redis_password and secrets/.redis_acl have been generated"
