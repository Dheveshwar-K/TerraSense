#!/usr/bin/env bash
set -euo pipefail

# Safe PostgreSQL Restore Script for TerraSense (PS-010)
# Usage: ./scripts/restore_postgres.sh <dump_file> <target_database_name>
# Restores into an explicit target database (never silently overwrites live DB without confirmation).

if [ "$#" -lt 2 ]; then
  echo "Usage: $0 <dump_file> <target_database_name>" >&2
  exit 1
fi

DUMP_FILE="$1"
TARGET_DB="$2"
CONTAINER_NAME="${POSTGRES_CONTAINER:-ps010_postgres}"
DB_USER="${POSTGRES_USER:-terrasense_app}"

if [ ! -f "${DUMP_FILE}" ]; then
  echo "ERROR: Dump file '${DUMP_FILE}' not found." >&2
  exit 1
fi

if [ -f "${DUMP_FILE}.sha256" ]; then
  echo "Verifying SHA-256 checksum..."
  sha256sum -c "${DUMP_FILE}.sha256"
fi

echo "Verifying dump readability..."
docker exec -i "${CONTAINER_NAME}" pg_restore --list < "${DUMP_FILE}" > /dev/null

read -r -p "Confirm restore of '${DUMP_FILE}' into target database '${TARGET_DB}'? (yes/no): " CONFIRM
if [ "${CONFIRM}" != "yes" ]; then
  echo "Restore cancelled."
  exit 0
fi

docker exec -i "${CONTAINER_NAME}" psql -U "${DB_USER}" -d postgres -c "CREATE DATABASE \"${TARGET_DB}\";" 2>/dev/null || true
docker exec -i "${CONTAINER_NAME}" pg_restore \
  -U "${DB_USER}" \
  -d "${TARGET_DB}" \
  --clean \
  --if-exists \
  --no-owner \
  --no-acl < "${DUMP_FILE}"

echo "Restore to '${TARGET_DB}' completed successfully."
