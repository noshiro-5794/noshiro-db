#!/usr/bin/env bash
# Restore a custom-format dump into a target database.
#
# Usage: restore_postgres.sh <dump-file> [target-database]
#
# The target database is created when missing and dropped first when it already
# exists, so the restore is repeatable. Restoring over the live database is
# refused unless RESTORE_ALLOW_PRODUCTION=true, because the safe path is to
# restore into a scratch database and point the application at it.
#
# Environment:
#   POSTGRES_CONTAINER     container running PostgreSQL (noshiro-db-postgres-1)
#   POSTGRES_USER          superuser used for create/drop (noshiro)
#   POSTGRES_DB            production database to protect (noshiro_db)
set -euo pipefail

dump_file="${1:-}"
target_db="${2:-}"

if [[ -z "${dump_file}" || ! -f "${dump_file}" ]]; then
  echo "usage: restore_postgres.sh <dump-file> [target-database]" >&2
  exit 1
fi

container="${POSTGRES_CONTAINER:-noshiro-db-postgres-1}"
user_name="${POSTGRES_USER:-noshiro}"
production_db="${POSTGRES_DB:-noshiro_db}"
target_db="${target_db:-${production_db}_restore}"

checksum_file="${dump_file}.sha256"
if [[ -f "${checksum_file}" ]]; then
  expected="$(cat "${checksum_file}")"
  if command -v sha256sum >/dev/null 2>&1; then
    actual="$(sha256sum "${dump_file}" | awk '{print $1}')"
  else
    actual="$(shasum -a 256 "${dump_file}" | awk '{print $1}')"
  fi
  if [[ "${expected}" != "${actual}" ]]; then
    echo "checksum mismatch for ${dump_file}" >&2
    exit 1
  fi
  echo "checksum verified"
fi

if [[ "${target_db}" == "${production_db}" && "${RESTORE_ALLOW_PRODUCTION:-false}" != "true" ]]; then
  echo "refusing to overwrite ${production_db}; set RESTORE_ALLOW_PRODUCTION=true to force" >&2
  exit 1
fi

echo "restoring ${dump_file} into ${target_db}"
docker exec "${container}" psql --username "${user_name}" --dbname postgres \
  --command "DROP DATABASE IF EXISTS \"${target_db}\""
docker exec "${container}" psql --username "${user_name}" --dbname postgres \
  --command "CREATE DATABASE \"${target_db}\""

docker exec --interactive "${container}" pg_restore \
  --username "${user_name}" \
  --dbname "${target_db}" \
  --no-owner \
  --exit-on-error \
  < "${dump_file}"

echo "restored ${target_db}"
