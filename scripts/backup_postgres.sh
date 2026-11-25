#!/usr/bin/env bash
set -euo pipefail

# Automated PostgreSQL Backup Script for TerraSense (PS-010)
# Usage: ./scripts/backup_postgres.sh [backup_dir] [retention_days]

BACKUP_DIR="${1:-./backups}"
RETENTION_DAYS="${2:-30}"
CONTAINER_NAME="${POSTGRES_CONTAINER:-ps010_postgres}"
DB_NAME="${POSTGRES_DB:-foundry_quality}"
DB_USER="${POSTGRES_USER:-terrasense_app}"
TIMESTAMP="$(date -u +%Y%m%d_%H%M%SZ)"
OUT_FILE="${BACKUP_DIR}/terrasense_${DB_NAME}_${TIMESTAMP}.dump"

mkdir -p "${BACKUP_DIR}"

echo "[$(date -u +%FT%TZ)] Starting PostgreSQL backup of '${DB_NAME}'..."
docker exec -t "${CONTAINER_NAME}" pg_dump \
  -U "${DB_USER}" \
  -d "${DB_NAME}" \
  --format=custom \
  --compress=9 \
  --no-owner \
  --no-acl > "${OUT_FILE}"

if [ ! -s "${OUT_FILE}" ]; then
  echo "ERROR: Backup file '${OUT_FILE}' is empty!" >&2
  rm -f "${OUT_FILE}"
  exit 1
fi

# Verify archive table-of-contents readability
docker exec -i "${CONTAINER_NAME}" pg_restore --list < "${OUT_FILE}" > /dev/null

sha256sum "${OUT_FILE}" > "${OUT_FILE}.sha256"
echo "[$(date -u +%FT%TZ)] Verified backup written to ${OUT_FILE}"

# Prune backups older than retention policy
find "${BACKUP_DIR}" -type f \( -name "terrasense_*.dump" -o -name "terrasense_*.dump.sha256" \) -mtime "+${RETENTION_DAYS}" -delete
echo "[$(date -u +%FT%TZ)] Backup complete (retention=${RETENTION_DAYS}d)."
