#!/bin/bash

# Variables
CONTAINER_NAME="your_postgres_container"
DB_NAME="your_database_name"
DB_USER="your_database_user"
BACKUP_DIR="/path/to/backup/directory"
DATE=$(date +%Y%m%d%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_backup_${DATE}.sql"

# Ensure the backup directory exists
mkdir -p ${BACKUP_DIR}

# Run pg_dump inside the Docker container
docker exec -t ${CONTAINER_NAME} pg_dump -U ${DB_USER} ${DB_NAME} > ${BACKUP_FILE}

# Print a message on completion
echo "Backup of database '${DB_NAME}' completed and saved as ${BACKUP_FILE}"

