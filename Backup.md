# Restoring the database
This page explains how you can restore the database of your container using one of 
the backed up SQL file created by the [backup-script](https://github.com/dumbstertruck3/care/blob/docker_backup/scripts/backup.sh).
> **Note:** This documentation assumes that you are using a linux based system
## Here how the script works
The script automates the process of creating PostgreSQL database backups from
a Docker container. It creates a backup sql file using the `pg dump` utility in PostgreSQL.
And stores these files in `/home/$USER/care-backups`, the script will create this if it does'nt exists. Files older than 7 days are deleted at
the time of executing the script. And it saves the file as `care_backup_%Y%m%d%H%M%S.sql`.

## How to restore the database
We are basically backing up the existing database then deleting the existing database and creating a new database with the same name. Run the commands as follows on your terminal.
> Make sure the containers down
```bash
make down
```
Move the sql file to the target directory thats mounted to the container.
```bash
sudo mv /home/$USER/care-backups/<file name> /home/$USER/care_dir-to-read
```
Bring up the contaier
```bash
make up
```
Backup the existing database
```bash
chmod +x /home/$USER/care/scripts/backup.sh
bash /home/$USER/care/scripts/backup.sh
```
Delete the existing database
```bash
docker exec -it $(docker ps --format '{{.Names}}' | grep 'care-db') psql -U postgres -c "CREATE DATABASE care;"
```
Create the new database
```bash
docker exec -it $(docker ps --format '{{.Names}}' | grep 'care-db') psql -U postgres -c "CREATE DATABASE care;"
```
Get inside the container
```bash
docker exec -it $(docker ps --format '{{.Names}}' | grep 'care-db') /bin/bash
```
Restore the database
```bash
cd backup
psql -U postgres -d care < $(ls -t | head -n 1)
```
> There are way easier ways to do this, if anyone has any particular idea do make a pr :)
