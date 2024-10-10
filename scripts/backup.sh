#!/bin/bash
# Variables
CONTAINER_NAME= $(docker ps --format '{{.Names}}' | grep 'care-db'
)
DB_NAME="care"
DB_USER="postgres"
#Adding separate directory
BACKUP_DIR="$(pwd)/backup"
DATE=$(date +%Y%m%d%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_backup_${DATE}.sql"

# Ensure the backup directory exists
mkdir -p ${BACKUP_DIR}

# Remove old backups
find ${BACKUP_DIR} -name "${DB_NAME}_backup_*.sql" -type f -mtime +0 -exec rm -f {} \;

# add the new backup
docker exec -t ${CONTAINER_NAME} pg_dump -U ${DB_USER} ${DB_NAME} > ${BACKUP_FILE}
echo "Backup of database '${DB_NAME}' completed and saved as ${BACKUP_FILE}"
