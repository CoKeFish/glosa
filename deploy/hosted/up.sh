#!/usr/bin/env bash
# Start or update glosa's hosted service on the VPS. Secrets are fetched from Doppler with the
# official CLI image, handed to docker compose through a pipe, and never written to disk.
#
#   deploy/hosted/up.sh            pull the images and (re)start
#   deploy/hosted/up.sh <args>     any other docker compose command, e.g. "ps" or "logs api"
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
token_file="${GLOSA_DOPPLER_TOKEN_FILE:-/opt/glosa-hosted/doppler-token}"
[ -r "$token_file" ] || { echo "Falta el token de Doppler en $token_file" >&2; exit 1; }

secrets() {
  docker run --rm -e DOPPLER_TOKEN="$(cat "$token_file")" dopplerhq/cli:3 \
    secrets download --no-file --format env
}

compose() {
  docker compose -f "$here/compose.yml" --env-file <(secrets) "$@"
}

if [ "$#" -eq 0 ]; then
  compose pull
  compose up -d --remove-orphans
  compose ps
else
  compose "$@"
fi
