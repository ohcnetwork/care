#!/bin/bash
set -ue
# Variables
container_name="$(docker ps --format '{{.Names}}' | grep 'care-db'
)"
db_name='care'
db_user='postgres'
#Adding separate directory
backup_dir="/home/$USER/care-backups"
date=$(date +%Y%m%d%H%M%S)
backup_file="${backup_dir}/${db_name}_backup_${date}.sql"

# Ensure the backup directory exists
[ -d "${backup_dir}" ] || mkdir "$backup_dir"

# Remove old backups
find "${backup_dir}" -name "${db_name}_backup_*.sql" -type f -mtime +7 -exec rm {} \;

# add the new backup
docker exec -t ${container_name} pg_dump -U ${db_user} ${db_name} > ${backup_file}
echo "Backup of database '${db_name}' completed and saved as ${backup_file}"
