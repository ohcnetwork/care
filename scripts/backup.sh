#!/bin/bash
set -ueo pipefail
# Ensure we can find the .env file
ENV_FILE="$(dirname "$(readlink -f "$0")")/../.env"
if [[ ! -f "${ENV_FILE}" ]]; then
    echo "Error: .env file not found at ${ENV_FILE}" >&2
    exit 1
fi
source "${ENV_FILE}"

container_name="$(docker ps --format '{{.Names}}' | grep 'care-db')"
if [[ -z "${container_name}" ]]; then
    echo "Error: PostgreSQL container 'care-db' is not running" >&2
    exit 1
    elif [[ $(echo "${container_name}" | wc -l) -gt 1 ]]; then
    echo "Error: Multiple containers matched 'care-db'" >&2
    exit 1
fi

date=$(date +%Y%m%d%H%M%S)
#name the file
backup_file="${POSTGRES_DB}_backup_${date}.dump"

# Remove old backup/backups
docker exec -t ${container_name} find "/backups" -name "${POSTGRES_DB}_backup_*.dump" -type f -mtime +${DB_BACKUP_RETENTION_PERIOD} -exec rm {} \;

#backup the database
docker exec -t ${container_name} pg_dump -U ${POSTGRES_USER} -Fc -f /backups/${backup_file} ${POSTGRES_DB}

if ! docker exec -t ${container_name} pg_dump -U ${POSTGRES_USER} -Fc -f /backups/${backup_file} ${POSTGRES_DB}; then
    echo "Error: Database backup failed" >&2
    exit 1
fi
echo "Backup of database '${POSTGRES_DB}' completed and saved as /backups/${backup_file}"
