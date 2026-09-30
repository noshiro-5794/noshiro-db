#!/usr/bin/env bash
# Mirror the MinIO data root into the backup root and record checksums.
#
# MinIO in this deployment persists to a bind mount, so a consistent copy can be
# taken from the host without the S3 API. Stop writes (or accept a
# point-in-time copy) before relying on it for recovery.
set -euo pipefail

data_root="${NOSHIRO_DATA_ROOT:-/vol1/1000/noshiro-data}"
backup_root="${NOSHIRO_BACKUP_ROOT:-/vol1/1000/noshiro-backup}"
source_dir="${data_root}/minio"
stamp="$(date +%Y%m%d-%H%M%S)"
target_dir="${backup_root}/minio/${stamp}"

if [[ ! -d "${source_dir}" ]]; then
  echo "minio data root ${source_dir} does not exist" >&2
  exit 1
fi

mkdir -p "${target_dir}"
echo "mirroring ${source_dir} -> ${target_dir}"
tar --create --file "${target_dir}/minio-data.tar" --directory "${source_dir}" .

if command -v sha256sum >/dev/null 2>&1; then
  sha256sum "${target_dir}/minio-data.tar" | awk '{print $1}' > "${target_dir}/minio-data.tar.sha256"
else
  shasum -a 256 "${target_dir}/minio-data.tar" | awk '{print $1}' > "${target_dir}/minio-data.tar.sha256"
fi

echo "backup written: ${target_dir}/minio-data.tar"
