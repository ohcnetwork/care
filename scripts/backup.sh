#!/bin/bash
set -ueo pipefail

# Ensure we can find the .env file
ENV_FILE="$(dirname "$(readlink -f "$0")")/../.env"
if [[ ! -f "${ENV_FILE}" ]]; then
    echo "Error: .env file not found at ${ENV_FILE}" >&2
    exit 1
fi
source "${ENV_FILE}"

# Logging function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a ./backup_db.log
}

# Function to send email using msmtp
send_email() {
    local subject="$1"
    local body="$2"

    if [[ -n "${EMAIL}" && -f ~/.msmtprc ]]; then
        log "Sending email to ${EMAIL} with subject: ${subject}"

        echo -e "From: ${EMAIL}\nTo: ${EMAIL}\nSubject: ${subject}\n\n${body} \n check care/.backup_db.log for more info" | msmtp "${EMAIL}"

        if [ $? -eq 0 ]; then
            log "Email sent successfully."
        else
            log "Failed to send email."
        fi
    else
        log "Email configuration not found. Skipping email notification."
    fi
}

# Function to send system notification
send_notification() {
    local message="$1"
    if command -v notify-send &> /dev/null; then
        log "Sending system notification: $message"
        notify-send "Database Backup" "$message"
    else
        log "System notification not available (install 'libnotify' for notifications)."
    fi
}

# Check if the PostgreSQL container is running
log "Checking for running PostgreSQL container..."
container_name="$(docker ps --format '{{.Names}}' | grep 'care-db' || true)"

if [[ -z "${container_name}" ]]; then
    error_msg="Error: PostgreSQL container 'care-db' is not running"
    log "$error_msg"
    send_email "Database Backup Failed" "$error_msg"
    send_notification "$error_msg"
    exit 1
elif [[ $(echo "${container_name}" | wc -l) -gt 1 ]]; then
    error_msg="Error: Multiple containers matched 'care-db'"
    log "$error_msg"
    send_email "Database Backup Failed" "$error_msg"
    send_notification "$error_msg"
    exit 1
fi
log "Found PostgreSQL container: ${container_name}"

# Generate backup file name
date=$(date +%Y%m%d%H%M%S)
backup_file="${POSTGRES_DB}_backup_${date}.dump"
log "Backup file: ${backup_file}"

# Remove old backups
log "Removing old backups older than ${DB_BACKUP_RETENTION_PERIOD} days..."
docker exec -t ${container_name} find "/backups" -name "${POSTGRES_DB}_backup_*.dump" -type f -mtime +${DB_BACKUP_RETENTION_PERIOD} -exec rm {} \;

# Backup the database
log "Starting database backup..."
if docker exec -t ${container_name} pg_dump -U ${POSTGRES_USER} -Fc -f /backups/${backup_file} ${POSTGRES_DB}; then
    success_msg="Backup of database '${POSTGRES_DB}' completed and saved as /backups/${backup_file}"
    log "$success_msg"
    send_notification "$success_msg"
else
    error_msg="Error: Database backup failed."
    log "$error_msg"
    send_email "Database Backup Failed" "$error_msg"
    send_notification "$error_msg"
    exit 1
fi
