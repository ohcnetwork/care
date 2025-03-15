#!/bin/bash

# Define variables
DB_CONTAINER=$(docker ps --format '{{.Names}}' | grep 'care-db')
BACKUP_DIR="./care-backups"
LOG_FILE="./restore_db.log"

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Check if the database container is running
if [ -z "$DB_CONTAINER" ]; then
    log_message "Error: No running database container found with name containing 'care-db'."
    exit 1
fi

# Stop all containers except the database
log_message "Stopping all containers except the database..."
docker ps --format '{{.Names}}' | grep -v "$DB_CONTAINER" | xargs -r docker stop >> "$LOG_FILE" 2>&1
if [ $? -ne 0 ]; then
    log_message "ERROR: Failed to stop containers. Check Docker logs."
    exit 1
fi

# Drop the existing database
log_message "Dropping existing 'care' database..."
docker exec -it "$DB_CONTAINER" psql -U postgres -c "DROP DATABASE IF EXISTS care;" >> "$LOG_FILE" 2>&1
if [ $? -ne 0 ]; then
    log_message "ERROR: Failed to drop database 'care'."
    exit 1
fi

# Create a new database
log_message "Creating a new 'care' database..."
docker exec -it "$DB_CONTAINER" psql -U postgres -c "CREATE DATABASE care;" >> "$LOG_FILE" 2>&1
if [ $? -ne 0 ]; then
    log_message "ERROR: Failed to create database 'care'."
    exit 1
fi

# List available backups with index
log_message "Available backups in $BACKUP_DIR:"
BACKUP_FILES=("$BACKUP_DIR"/*)
if [ ${#BACKUP_FILES[@]} -eq 0 ]; then
    log_message "No backup files found."
    exit 1
fi

for i in "${!BACKUP_FILES[@]}"; do
    log_message "[$i] ${BACKUP_FILES[$i]##*/}"
done

# Ask user for the index of the backup file to restore
read -p "Enter the index of the backup file to restore: " INDEX

# Validate index
if ! [[ "$INDEX" =~ ^[0-9]+$ ]] || [ "$INDEX" -lt 0 ] || [ "$INDEX" -ge "${#BACKUP_FILES[@]}" ]; then
    log_message "Invalid index. Exiting."
    exit 1
fi

BACKUP_FILE="${BACKUP_FILES[$INDEX]}"
BACKUP_FILE_NAME=$(basename "$BACKUP_FILE")

# Restore the database
log_message "Restoring database from $BACKUP_FILE_NAME..."
docker exec -i "$DB_CONTAINER" pg_restore -U postgres -d care < "$BACKUP_FILE" >> "$LOG_FILE" 2>&1
if [ $? -ne 0 ]; then
    log_message "ERROR: Failed to restore database from $BACKUP_FILE_NAME."
    exit 1
fi


log_message "Database restore completed successfully."
