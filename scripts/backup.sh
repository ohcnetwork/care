#!/bin/bash
set -ue
source ../.env

container_name="$(docker ps --format '{{.Names}}' | grep 'care-db')"
date=$(date +%Y%m%d%H%M%S)
#name the file
backup_file="./backup/${POSTGRES_DB}_backup_${date}.dump"

# Remove old backups
docker exec -t ${container_name} find "./backup" -name "${POSTGRES_DB}_backup_*.dump" -type f -mtime +${RETENTION_PERIOD} -exec rm {} \;

#backup the database
docker exec -t ${container_name} pg_dump -U ${POSTGRES_USER} -Fc -f ${backup_file} ${POSTGRES_DB}
echo "Backup of database '${POSTGRES_DB}' completed and saved as ${backup_file}"
