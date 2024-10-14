Docker database backup
======================

This page explains how to automate the backup process of a Docker database on a daily basis and restore the backup snapshot created by the `backup script <scripts/backup.sh>`_.

   Note: This documentation assumes that you are using a Linux-based system.
-------------------------------------------------------------------------------

Here's how the script works
---------------------------

The script automates the process of creating PostgreSQL database backups from a Docker container. It generates a backup SQL file using the pg_dump utility in PostgreSQL and stores these files in ``/home/$USER/care-backups.`` The script will create this directory if it doesn't already exist. Backup files older than 7 days are deleted when the script is executed. The backup file is saved with the name ``care_backup_%Y%m%d%H%M%S.sql.``

Set up a cronjob
----------------

Backup your database running on docker automatically everyday by initiating a cronjob.

    **Note**: Make sure you have the docker containers up and running, refer `this <../local-setup/configuration.rst>`_.

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

We are first backing up the existing database, then deleting it, and finally creating a new database with the same name. Run the following commands in your terminal.

Make sure the containers are down:

.. code:: bash

   make down

Move the SQL file to the target directory that's mounted to the container:

.. code:: bash

   sudo mv /home/$USER/care-backups/<file name> /home/$USER/care_dir-to-read

Bring up the container:

.. code:: bash

   make up

Backup the existing database:

.. code:: bash

   chmod +x /home/$USER/care/scripts/backup.sh
   bash /home/$USER/care/scripts/backup.sh

Delete the existing database:

.. code:: bash

   docker exec -it $(docker ps --format '{{.Names}}' | grep 'care-db') psql -U postgres -c "DROP DATABASE IF EXISTS care;"

Create the new database:

.. code:: bash

   docker exec -it $(docker ps --format '{{.Names}}' | grep 'care-db') psql -U postgres -c "CREATE DATABASE care;"

Get inside the container:

.. code:: bash

   docker exec -it $(docker ps --format '{{.Names}}' | grep 'care-db') /bin/bash

Restore the database:

.. code:: bash

   cd backup
   psql -U postgres -d care < $(ls -t | head -n 1)

------------------------------------------------------------------------------------------------------------------

  There are way easier ways to do this. If anyone has any particular idea, feel free to make a PR :)



