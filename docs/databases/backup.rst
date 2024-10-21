Docker database backup
======================

This page explains how to automate the backup process of a Docker database on a daily basis and restore the backup snapshot created by the `backup script <../../scripts/backup.sh>`_.

   Note: This documentation assumes that you are using a Linux-based system.
-------------------------------------------------------------------------------

Here's how the script works
---------------------------

The script automates the process of creating PostgreSQL database backups from a Docker container. It generates a backup file(``.dump``) using the pg_dump utility in PostgreSQL and stores these files in ``/home/$USER/care-backups.`` which is binded to ``/backups`` in the docker container. Backup files older than 7 days are deleted when the script is executed. The backup file is saved with the name ``care_backup_%Y%m%d%H%M%S.sql``.

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

Open up a crontab:

.. code:: bash

 crontab -e

Add the cronjob:

.. code:: bash

 0 0 * * * /home/care/scripts/backup.sh

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

Restoration of the Database
===========================

We are basically deleting the container's existing database and creating a new database with the same name. Then we will use ``pg_restore`` to restore the database. Run the following commands in your terminal.

Delete the existing database:

.. code:: bash

   docker exec -it $(docker ps --format '{{.Names}}' | grep 'care-db') psql -U postgres -c "DROP DATABASE IF EXISTS care;"

Create the new database:

.. code:: bash

   docker exec -it $(docker ps --format '{{.Names}}' | grep 'care-db') psql -U postgres -c "CREATE DATABASE care;"

Execute and copy the name of the file you want to restore the database with:

.. code:: bash

   sudo ls /home/$USER/care-backups/

Restore the database:

    Replace <file name> with your file name which looks like this ``care_backup_%Y%m%d%H%M%S.sql``

.. code:: bash

   docker exec -it $(docker ps --format '{{.Names}}' | grep 'care-db') pg_restore -U postgres -d care /backups/<file name>.

------------------------------------------------------------------------------------------------------------------

  There are way easier ways to do this. If anyone has any particular idea, feel free to make a PR :)



