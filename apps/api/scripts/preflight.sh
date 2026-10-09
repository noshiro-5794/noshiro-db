#!/usr/bin/env bash
# Validate the Compose files, Django configuration, and migration drift.
#
# Runs before a deploy and never touches the production database: the Compose
# check only renders the files, and the Django checks run against local settings
# unless ENV_FILE points at a real environment file.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"

env_file="${ENV_FILE:-.env}"
compose_env_file="${COMPOSE_ENV_FILE:-${env_file}}"

echo "== compose config =="
for file in docker-compose.infra.yml docker-compose.app.yml; do
  ENV_FILE="${env_file}" docker compose \
    --env-file "${compose_env_file}" \
    -f "${file}" config --quiet
  echo "  ${file} ok"
done

echo "== ruff =="
uv run ruff check .
uv run ruff format --check src tests

echo "== django checks =="
uv run python src/manage.py check
uv run python src/manage.py makemigrations --check --dry-run

echo "== openapi snapshot =="
snapshot="$(mktemp)"
trap 'rm -f "${snapshot}"' EXIT
uv run python src/manage.py spectacular \
  --format openapi-json \
  --file "${snapshot}"
if ! diff -q "${snapshot}" tests/snapshots/openapi.json >/dev/null; then
  echo "tests/snapshots/openapi.json is stale; regenerate it with make openapi" >&2
  exit 1
fi
echo "  snapshot current"

echo "preflight ok"
