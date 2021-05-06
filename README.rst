Care
====
    
Care is a Corona Care Center management app for the Govt of Kerala
====

Auto Deployed to https://careapi.coronasafe.in for master Branch. 

Report bugs with Github Issues

.. image:: https://api.codacy.com/project/badge/Grade/3ca2f379f8494605b52b382639510e0a
   :alt: Codacy Badge
   :target: https://app.codacy.com/gh/coronasafe/care?utm_source=github.com&utm_medium=referral&utm_content=coronasafe/care&utm_campaign=Badge_Grade_Dashboard
.. image:: https://img.shields.io/circleci/build/github/coronasafe/care/master?style=flat-square
    :alt: Circle CI build
    :target: https://circleci.com/gh/coronasafe/care    
.. image:: https://github.com/coronasafe/care/workflows/Code%20scanning%20-%20action/badge.svg
    :alt: Code scanning

   
.. image:: https://img.shields.io/badge/built%20with-Cookiecutter%20Django-ff69b4.svg
     :target: https://github.com/pydanny/cookiecutter-django/
     :alt: Built with Cookiecutter Django
.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
     :target: https://github.com/ambv/black
     :alt: Black code style


.. image:: https://i.imgur.com/V7jxjak.png
     :target: http://slack.coronasafe.in/
     :alt: Join CoronaSafe Slack channel

:License: MIT

Set up Local environment
------------------------

Install PostgreSQL.
If you are installing PostgreSQL for the first time, follow the steps given in this answer_ to setup password based authentication.

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

You also might have to install PostGIS scripts.

* Linux users can install PostGIS scripts by running ::

    $ sudo apt install postgresql-<version>-postgis-scripts

* Windows users can install
    - PostGIS through Application Stack Builder which is installed along PostgreSQL using standard PostgreSQL installer.
    - OSGeo4W from this site_. 

Then follow the steps listed here_.

Setting up Pre-Commit
^^^^^^^^^^^^^^^^^^^^^
Git hooks is a feature which helps to fix small issues in your code before you commit the code.
Pre-Commit is a package manager and tool for running and organising your git hooks. More here at pre_commit_site_.

* Install pre-commit
    pre-commit is installed while you run ::

     pip install -r requirements/local.txt

* Setup
    this installs all the git-hooks ::

    $ pre-commit install

* Running pre-commits
    The git hooks run every time you commit code to the repo.
    If you want to run it before committing, use the following command ::

    $ pre-commit run --all-files

* FAQs and Issues with pre-commit
    - Reach out on the #coronasafe_django channel in slack to resolve the issues.

.. _here: https://cookiecutter-django.readthedocs.io/en/latest/developing-locally.html
.. _answer: https://stackoverflow.com/a/12670521/4385622
.. _pre_commit_site: https://pre-commit.com/
.. _site: https://trac.osgeo.org/osgeo4w/

Settings
--------

Moved to settings_.

.. _settings: http://cookiecutter-django.readthedocs.io/en/latest/settings.html

Basic Commands
--------------

Setting Up Your Users
^^^^^^^^^^^^^^^^^^^^^

* To create a **normal user account**, just go to Sign Up and fill out the form. Once you submit it, you'll see a "Verify Your E-mail Address" page. Go to your console to see a simulated email verification message. Copy the link into your browser. Now the user's email should be verified and ready to go.

* To create an **superuser account**, use this command::

    $ python manage.py createsuperuser

For convenience, you can keep your normal user logged in on Chrome and your superuser logged in on Firefox (or similar), so that you can see how the site behaves for both kinds of users.

If the command prompts for username only and after entering if it goes to error
do make sure that you have done the following 

Note: Make sure that you have created a database named `care` (replace thisw with your database name)  with privileges set for the user `postgres`

In the virtualenv shell type the following commands also::

 export DATABASE_URL=postgres://postgres:<password>@127.0.0.1:5432/care

 export TEST_POSTGIS_URL="postgis://postgres:<password>@127.0.0.1:5432/care"

You may replace 'care' with the database you have created before.

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

$ python manage.py collectstatic

This will copy static files (css, js, images) into the care/care/media directory so that the website loads with images and CSS styles. When prompted to confirm, enter "yes".


Type checks
^^^^^^^^^^^

Running type checks with mypy:

::

  $ mypy care

Run Tests
^^^^^^^^^^^^^
::

   $ python manage.py test --settings=config.settings.test -n

If you get an :code:`ImproperlyConfigured` error regarding the Spatialite library extension, install it with the command:

::

  $ sudo apt install libsqlite3-mod-spatialite

Live reloading and Sass CSS compilation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Moved to `Live reloading and SASS compilation`_.

.. _`Live reloading and SASS compilation`: http://cookiecutter-django.readthedocs.io/en/latest/live-reloading-and-sass-compilation.html




Email Server
^^^^^^^^^^^^

In development, it is often nice to be able to see emails that are being sent from your application. If you choose to use `MailHog`_ when generating the project a local SMTP server with a web interface will be available.

#. `Download the latest MailHog release`_ for your OS.
[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2Fcoronasafe%2Fcare.svg?type=shield)](https://app.fossa.com/projects/git%2Bgithub.com%2Fcoronasafe%2Fcare?ref=badge_shield)


#. Rename the build to ``MailHog``.

#. Copy the file to the project root.

#. Make it executable: ::

    $ chmod +x MailHog

#. Spin up another terminal window and start it there: ::

    ./MailHog

#. Check out `<http://127.0.0.1:8025/>`_ to see how it goes.

Now you have your own mail server running locally, ready to receive whatever you send it.

.. _`Download the latest MailHog release`: https://github.com/mailhog/MailHog/releases

.. _mailhog: https://github.com/mailhog/MailHog



Sentry
^^^^^^

Sentry is an error logging aggregator service. You can sign up for a free account at  https://sentry.io/signup/?code=cookiecutter  or download and host it yourself.
The system is setup with reasonable defaults, including 404 logging and integration with the WSGI application.

You must set the DSN url in production.


Deployment
----------

The following details how to deploy this application.


Heroku
^^^^^^

See detailed `cookiecutter-django Heroku documentation`_.

.. _`cookiecutter-django Heroku documentation`: http://cookiecutter-django.readthedocs.io/en/latest/deployment-on-heroku.html


## License
[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2Fcoronasafe%2Fcare.svg?type=large)](https://app.fossa.com/projects/git%2Bgithub.com%2Fcoronasafe%2Fcare?ref=badge_large)
 
