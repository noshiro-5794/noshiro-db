#!/usr/bin/env bash
# Write a checksummed custom-format dump of the production database.
#
# Environment:
#   POSTGRES_CONTAINER             container running PostgreSQL (noshiro-db-postgres-1)
#   POSTGRES_USER / POSTGRES_DB    credentials used by pg_dump (noshiro / noshiro_db)
#   NOSHIRO_BACKUP_ROOT            destination root (/vol1/1000/noshiro-backup)
#   POSTGRES_BACKUP_RETENTION_DAYS keep this many days of dumps (14)
set -euo pipefail

container="${POSTGRES_CONTAINER:-noshiro-db-postgres-1}"
user_name="${POSTGRES_USER:-noshiro}"
db_name="${POSTGRES_DB:-noshiro_db}"
backup_root="${NOSHIRO_BACKUP_ROOT:-/vol1/1000/noshiro-backup}"
retention_days="${POSTGRES_BACKUP_RETENTION_DAYS:-14}"

if [[ ! -d "${backup_root}" ]]; then
  echo "backup root ${backup_root} does not exist" >&2
  exit 1
fi

target_dir="${backup_root}/postgres"
mkdir -p "${target_dir}"
stamp="$(date +%Y%m%d-%H%M%S)"
dump_file="${target_dir}/${db_name}-${stamp}.dump"

echo "dumping ${db_name} from ${container} -> ${dump_file}"
docker exec "${container}" pg_dump \
  --username "${user_name}" \
  --dbname "${db_name}" \
  --format custom \
  --no-owner \
  > "${dump_file}"

if [[ ! -s "${dump_file}" ]]; then
  echo "dump is empty; refusing to keep it" >&2
  rm -f "${dump_file}"
  exit 1
fi

if command -v sha256sum >/dev/null 2>&1; then
  sha256sum "${dump_file}" | awk '{print $1}' > "${dump_file}.sha256"
else
  shasum -a 256 "${dump_file}" | awk '{print $1}' > "${dump_file}.sha256"
fi

# Prune old dumps only after a verified-good one exists.
find "${target_dir}" -name "${db_name}-*.dump" -mtime "+${retention_days}" -print -delete || true
find "${target_dir}" -name "${db_name}-*.dump.sha256" -mtime "+${retention_days}" -print -delete || true

echo "backup written: ${dump_file}"
echo "checksum:       $(cat "${dump_file}.sha256")"
