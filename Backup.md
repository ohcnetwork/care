# Restoring the database
This page explains how you can restore the database of your container using one of 
the backed up SQL file created by the [backup-script](https://github.com/dumbstertruck3/care/blob/docker_backup/scripts/backup.sh).
> **Note:** This documentation assumes that you are using a linux based system
## Here how the script works
The script automates the process of creating PostgreSQL database backups from
a Docker container. It creates a backup sql file using the `pg dump` utility in PostgreSQL.
And stores these files in `/home/$USER/care-backups`. Files older than 7 days are deleted at
the time of executing the script. And it saves the file as `care_backup_%Y%m%d%H%M%S.sql`.

## How to restore the database
