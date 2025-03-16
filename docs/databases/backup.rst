Docker Database Backup
======================

This page explains how to automate the backup process of a Docker-based PostgreSQL database on a daily basis and restore the backup snapshot created by the `backup.sh <../../scripts/backup.sh>`_ script.

    Note: This documentation assumes you are using a Linux-based system.

How the Script Works
--------------------

The script automates the process of creating PostgreSQL database backups from a Docker container. It generates a backup file (``.dump``) using the pg_dump utility in PostgreSQL and stores these files in the directory specified by the ``$BACKUP_DIR`` environment variable, which is mounted to ``/backups`` inside the Docker container. In case of a backup failure, the script will send a system notification and an email if configured. For troubleshooting, logs can be found at ``./backup_db.log``.


Backup files older than `$DB_BACKUP_RETENTION_PERIOD <../../.env.example>`_ days are automatically deleted when the script runs. By default, this retention period is set to **7 days**.

Backup files are named using the following format:

``care_backup_%Y%m%d%H%M%S.sql``

Install Packages and Automate the Cron Job
------------------------------------------

This script installs required packagesf or backups based on the OS (Debian or Fedora-based) and sets up a cron job to run /scripts/backup.sh daily at midnight.

    Note: This script is compatible with **Fedora** and **Debian-based** systems only, and make sure you are inside the care directory when you are setting this up.

Make the Script Executable and Run It
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   chmod +x /scripts/backup_setup.sh
   ./scripts/backup_setup.sh

List the Cron Jobs
~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   crontab -l

Check the Status of Cron
~~~~~~~~~~~~~~~~~~~~~~~~

For Fedora-based systems:

.. code-block:: bash

   sudo systemctl status crond

For Debian-based systems:

.. code-block:: bash

   sudo systemctl status cron

Verify the Cron Job
~~~~~~~~~~~~~~~~~~~

To confirm the cron job is running:

1. Check system logs for cron activity:

   .. code-block:: bash

      ls /var/log/

2. Monitor the backup directory for new files after the scheduled backup time.

Configure the SMTP Config File
==============================

To receive an email notification when a backup fails, configure your SMTP settings:

-----------------------------------
    
    Note: You need to set up an `App Password <https://myaccount.google.com/apppasswords>`_ for Gmail authentication.


For Fedora-based systems:
--------------------------

.. code-block:: bash

   nano ~/.msmtprc

Configuration for Fedora SMTP:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: ini

   # ~/.msmtprc
   defaults
   auth           on
   tls            on
   tls_trust_file /etc/ssl/certs/ca-certificates.crt
   logfile        ~/.msmtp.log

   # Account details
   account        gmail
   host           smtp.gmail.com
   port           587
   from           your_email@gmail.com
   user           your_email@gmail.com
   password       your_app_password

   # Set default account
   account default : gmail

For Debian-based systems:
-------------------------

.. code-block:: bash

   nano ~/.msmtprc

Configuration for Debian SMTP:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: ini

   # ~/.msmtprc
   defaults
   auth           on
   tls            on
   tls_trust_file /etc/ssl/certs/ca-certificates.crt
   logfile        ~/.msmtp.log

   # Account details
   account        gmail
   host           smtp.gmail.com
   port           587
   from           your_email@gmail.com
   user           your_email@gmail.com
   password       your_app_password
   # Set default account
   account default : gmail
------------------------------------------

    Note: Ensure your email address is also added to the environment variables (`env <../../.env.example>`_).

Restoring the Database
======================
    
    Make sure you have stopped all the containers that are dependant on the ``care-db`` except the ``care-db`` before proceeding. And be inside the care directory at the time of executing the following.

This script restores a PostgreSQL database (care) from a backup file. Restoring the database involves deleting the existing database, creating a new one, and using ``pg_restore`` to restore the backup. The script identifies the database container, stops all other containers, lists available backups for user selection, and restores the chosen backup. All actions and errors are logged in ``./restore_db.log`` for tracking and troubleshooting.

Make the script executable and run

.. code-block:: bash

    chmod +x /scripts/restore_backup.sh
    ./scripts/restore_backup.sh
---------------------------------------------
    
    After successfull restoration restart the containers
