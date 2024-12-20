Setting up development environment
===================================

There are two ways to run the development server:

    1. `Using Docker Compose`_ (most recommended)
    2. `Setup it manually <#manual-setup>`__ (if you don't have Docker Compose)


Using Docker Compose
---------------------

    This setup will run 5 Docker containers:

    - postgres (database)
    - care (main repo)
    - redis (in-memory cache)
    - celery (task queue)
    - minio (to mimic AWS services locally)

This is the most recommended way of setting up care locally,
as it installs appropriate dependencies in containers so there
is no chance of conflicting dependencies. If you are running this
first time, it might take a while depending upon your internet speed and machine specs.

- Steps to run the development server:

    1. Run the following command to start the development environment:
        .. code-block:: bash

            $ make up

    2. To load dummy data for testing run:
        .. code-block:: bash

            $ make load-dummy-data

    2. Open a browser and go to `http://localhost:9000`

- To stop the development environment:
    .. code-block:: bash

        $ make down

- To run tests:
    .. code-block:: bash

        $ make test


Manual setup
------------


Setting up postgres for the first time
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
After installation of Postgresql

Run::

    sudo psql -U postgres

If you see error::

    FATAL: Peer authentication failed for user "postgres"FATAL: Peer authentication failed for user "postgres"

Do the following steps to set up password authentication.

::

    sudo -u postgres psql

In the `postgres#` shell type::

\password postgres

to change the password

Exit psql::

    \q

Edit `/etc/postgresql/<postgres-version>/main/pg_hba.conf` and change:

::


 local    all        postgres                               peer

To::

 local    all        postgres                               md5

Restart postgresql::

 sudo service postgresql restart


Login to the postgres shell and run:

::

 CREATE DATABASE care;
 GRANT ALL PRIVILEGES ON DATABASE care TO postgres;
 \q

You may replace `care` with the database name of your preference

Then follow the steps listed here_.

Setting up Pre-Commit
^^^^^^^^^^^^^^^^^^^^^
Git hooks is a feature which helps to fix small issues in your code before you commit the code.
Pre-Commit is a package manager and tool for running and organising your git hooks. More here at pre_commit_site_.

* Install pre-commit
    pre-commit is installed while you run ::

     pipenv install --categories "packages dev-packages"

* Setup
    this installs all the git-hooks ::

    $ pre-commit install

* Running pre-commits
    The git hooks run every time you commit code to the repo.
    If you want to run it before committing, use the following command ::

    $ pre-commit run --all-files

* FAQs and Issues with pre-commit
    - Reach out on the #care_backend channel in slack to resolve the issues.

.. _here: https://cookiecutter-django.readthedocs.io/en/latest/developing-locally.html
.. _pre_commit_site: https://pre-commit.com/
.. _site: https://trac.osgeo.org/osgeo4w/

Basic Commands
^^^^^^^^^^^^^^

Setting Up Your Users
~~~~~~~~~~~~~~~~~~~~~

* To create an **superuser account**, run this command::

    $ python manage.py createsuperuser

If the command prompts for username only and after entering if it goes to error
do make sure that you have done the following

Note: Make sure that you have created a database named `care` (replace thisw with your database name)  with privileges set for the user `postgres`

In the virtualenv shell type the following commands also::

 export DATABASE_URL=postgres://postgres:<password>@127.0.0.1:5432/care

You may replace **care** with the database you have created before.

After doing this you can type the following command::

    $ python manage.py migrate

and after you make sure everything is ok

run this command again::

$ python manage.py createsuperuser

This will now prompt for the following details - Ignore any warnings.

- username: give the username here
- usertype: Give the value `10` [5 for doctor, 10 for hospital staff/hospital administrator, 15 for patient, 20 for volunteer]
- gender: 1 for male, 2 for female, 3 for other
- email: give e-mail id
- phonenumber: give your ten digit phone number here
- password: Give the password here

To copy static files (css, js, images) into the care/care/media directory so that the website loads with images and CSS styles, you may use the command:

::

$ python manage.py collectstatic

To load dummy data for testing run::

    $ python manage.py load_dummy_data


Type checks
~~~~~~~~~~~

Running type checks with mypy:

::

  $ mypy care

Run Tests
~~~~~~~~~
::

   $ python manage.py test --settings=config.settings.test -n

If you get an :code:`ImproperlyConfigured` error regarding the Spatialite library extension, install it with the command:

::

  $ sudo apt install libsqlite3-mod-spatialite
