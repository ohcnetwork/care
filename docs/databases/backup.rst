Restoring the Database
======================

This page explains how you can restore the database of your container using one of
the backed up SQL files created by the `backup-script <https://github.com/dumbstertruck3/care/blob/docker_backup/scripts/backup.sh>`_.

.. note::

   **Note:** This documentation assumes that you are using a Linux-based system.

Here is how the script works
============================

The script automates the process of creating PostgreSQL database backups from
a Docker container. It creates a backup SQL file using the ``pg_dump`` utility in PostgreSQL
and stores these files in ``/home/$USER/care-backups``. The script will create this directory if it doesn't exist. Files older than 7 days are deleted at
the time of executing the script. The file is saved as ``care_backup_%Y%m%d%H%M%S.sql``.

How to Restore the Database
===========================

We are essentially backing up the existing database, deleting the existing database, and creating a new database with the same name. Run the following commands in your terminal.

Make sure the containers are down::

   make down

Move the SQL file to the target directory that's mounted to the container::

   sudo mv /home/$USER/care-backups/<file name> /home/$USER/care_dir-to-read

Bring up the container::

   make up

Backup the existing database::

   chmod +x /home/$USER/care/scripts/backup.sh
   bash /home/$USER/care/scripts/backup.sh

Delete the existing database::

   docker exec -it $(docker ps --format '{{.Names}}' | grep 'care-db') psql -U postgres -c "DROP DATABASE IF EXISTS care;"

Create the new database::

   docker exec -it $(docker ps --format '{{.Names}}' | grep 'care-db') psql -U postgres -c "CREATE DATABASE care;"

Get inside the container::

   docker exec -it $(docker ps --format '{{.Names}}' | grep 'care-db') /bin/bash

Restore the database::

   cd backup
   psql -U postgres -d care < $(ls -t | head -n 1)

.. note::

   There are way easier ways to do this. If anyone has any particular idea, feel free to make a PR :)
