Docker database backup
======================

This page explains how to automate the backup process of a Docker database on a daily basis and restore the backup snapshot created by the `backup script <../../scripts/backup.sh>`_.

   Note: This documentation assumes that you are using a Linux-based system.
-------------------------------------------------------------------------------

Here's how the script works
---------------------------

The script automates the process of creating PostgreSQL database backups from a Docker container. It generates a backup file(``.dump``) using the pg_dump utility in PostgreSQL and stores these files in the path configured in  ``$BACKUP_DIR`` environment variable which is binded to ``/backups`` in the docker container. Backup files older than ``$DB_BACKUP_RETENTION_PERIOD`` days are deleted when the script is executed by default it is set to 7 days. The backup file is saved with the name ``care_backup_%Y%m%d%H%M%S.sql``.

Set up a cronjob
----------------

Backup your database running on docker automatically everyday by initiating a cronjob.

Install the package
~~~~~~~~~~~~~~~~~~~

For a fedora based system:

.. code:: bash

 sudo dnf install crond

For a debian based system:

.. code:: bash

 sudo apt install cron

Automate the cronjob
~~~~~~~~~~~~~~~~~~~~
   Note: Make sure you are inside the care directory at the time of executing the following.
-------------------------------------------------------------------------------

Open up a crontab:

.. code:: bash

 crontab -e

Add the cronjob:

.. code:: bash

 0 0 * * * "/scripts/backup.sh"

List the cron jobs
~~~~~~~~~~~~~~~~~~

.. code:: bash

 crontab -l

Check the status of cron
~~~~~~~~~~~~~~~~~~~~~~~~

For a fedora based os:

.. code:: bash

 sudo systemctl status crond

For a debian based os:

.. code:: bash

 sudo systemctl status cron

Verify the cron job
~~~~~~~~~~~~~~~~~
To verify the cron job is working:

1. Check the system logs for cron activity, which is usually somewhere in

   .. code:: bash

    /var/log/

2. Monitor the backup directory for new files after the scheduled time

Restoration of the Database
===========================

We are basically deleting the container's existing database and creating a new database with the same name. Then we will use ``pg_restore`` to restore the database. Run the following commands in your terminal.

   Make sure you have stopped all the containers except the db before proceeding. And be inside the care directory at the time of executing the following.
------------------------------------------------------------------------------

Delete the existing database:

.. code:: bash

   docker exec -it $(docker ps --format '{{.Names}}' | grep 'care-db') psql -U postgres -c "DROP DATABASE IF EXISTS care;"

Create the new database:

.. code:: bash

   docker exec -it $(docker ps --format '{{.Names}}' | grep 'care-db') psql -U postgres -c "CREATE DATABASE care;"

Execute and copy the name of the file you want to restore the database with:

.. code:: bash

   sudo ls ./care-backups

Restore the database:

    Replace <file name> with your file name which looks like this ``care_backup_%Y%m%d%H%M%S.sql``

.. code:: bash

   docker exec -it $(docker ps --format '{{.Names}}' | grep 'care-db') pg_restore -U postgres -d care /backups/<file name>.dump

------------------------------------------------------------------------------------------------------------------

  There are way easier ways to do this. If anyone has any particular idea, feel free to make a PR :)
