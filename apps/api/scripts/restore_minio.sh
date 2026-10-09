#!/usr/bin/env bash
# Restore a MinIO archive produced by scripts/backup_minio.sh.
#
# Usage: restore_minio.sh <archive.tar> [target-directory]
#
# The archive is unpacked into the target directory; the caller decides whether
# that is the live data root or a staging path.
set -euo pipefail

archive="${1:-}"
target_dir="${2:-${NOSHIRO_DATA_ROOT:-/vol1/1000/noshiro-data}/minio}"

if [[ -z "${archive}" || ! -f "${archive}" ]]; then
  echo "usage: restore_minio.sh <archive.tar> [target-directory]" >&2
  exit 1
fi

checksum_file="${archive}.sha256"
if [[ -f "${checksum_file}" ]]; then
  expected="$(cat "${checksum_file}")"
  if command -v sha256sum >/dev/null 2>&1; then
    actual="$(sha256sum "${archive}" | awk '{print $1}')"
  else
    actual="$(shasum -a 256 "${archive}" | awk '{print $1}')"
  fi
  if [[ "${expected}" != "${actual}" ]]; then
    echo "checksum mismatch for ${archive}" >&2
    exit 1
  fi
  echo "checksum verified"
fi

mkdir -p "${target_dir}"
echo "restoring ${archive} into ${target_dir}"
tar --extract --file "${archive}" --directory "${target_dir}"
echo "restored ${target_dir}"
