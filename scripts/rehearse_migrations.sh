#!/usr/bin/env bash
# Restore a dump into a throwaway PostgreSQL and apply migrations to it.
#
# The production database is never the first environment to see a migration.
# Usage: rehearse_migrations.sh [dump-file]   (defaults to the newest dump)
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"

env_file="${ENV_FILE:-.env.production}"
backup_root="${NOSHIRO_BACKUP_ROOT:-/vol1/1000/noshiro-backup}"
db_name="${POSTGRES_DB:-noshiro_db}"
user_name="${POSTGRES_USER:-noshiro}"
image="${APP_IMAGE:-noshiro-db/backend}:${APP_IMAGE_TAG:-local}"
rehearsal_container="noshiro-db-rehearsal-pg"
rehearsal_network="${COMPOSE_PROJECT_NAME:-noshiro-db}_noshiro_net"

dump_file="${1:-}"
if [[ -z "${dump_file}" ]]; then
  dump_file="$(find "${backup_root}/postgres" -name "*.dump" -print 2>/dev/null | sort | tail -1)"
fi
if [[ -z "${dump_file}" || ! -f "${dump_file}" ]]; then
  echo "no dump found; run scripts/backup_postgres.sh first" >&2
  exit 1
fi

cleanup() {
  docker rm -f "${rehearsal_container}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

cleanup
echo "starting throwaway PostgreSQL for ${dump_file}"
docker run --detach --name "${rehearsal_container}" \
  --network "${rehearsal_network}" \
  --env POSTGRES_PASSWORD=rehearsal \
  --env POSTGRES_USER="${user_name}" \
  --env POSTGRES_DB=rehearsal \
  postgres:15.18-bookworm >/dev/null

for _ in $(seq 1 60); do
  if docker exec "${rehearsal_container}" pg_isready --username "${user_name}" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

echo "restoring dump"
docker exec --interactive "${rehearsal_container}" pg_restore \
  --username "${user_name}" --dbname rehearsal --no-owner --exit-on-error \
  < "${dump_file}"

echo "applying migrations against the restored copy"
docker run --rm --network "${rehearsal_network}" \
  --env-file "${env_file}" \
  --env DATABASE_URL="postgresql://${user_name}:rehearsal@${rehearsal_container}:5432/rehearsal" \
  --env REQUIRE_DATABASE_URL_SCHEME=postgresql \
  "${image}" \
  python /app/src/manage.py migrate --noinput

echo "migration rehearsal ok (${db_name} untouched)"
