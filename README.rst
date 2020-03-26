Care
====

.. image:: https://api.codacy.com/project/badge/Grade/3ca2f379f8494605b52b382639510e0a
   :alt: Codacy Badge
   :target: https://app.codacy.com/gh/coronasafe/care?utm_source=github.com&utm_medium=referral&utm_content=coronasafe/care&utm_campaign=Badge_Grade_Dashboard

Care is a Corona Care Center management app for the Govt of Kerala

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

You also might have to install PostGIS scripts.

* Linux users can install PostGIS scripts by running ::

    $ sudo apt install postgresql-<version>-postgis-scripts

* Windows users can install PostGIS through Application Stack Builder which is installed along PostgreSQL using standard PostgreSQL installer.

Then follow the steps listed here_.

Setting up Pre-Commit
^^^^^^^^^^^^^^^^^^^^^
Git hooks is a feature which helps to fix small issues in your code before you commit the code.
Pre-Commit is a package manager and tool for running and organising your git hooks. More here at pre_commit_site_.

* Install pre-commit
    pre-commit is installed while you run `pip install -r requirements/local.txt`

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

Type checks
^^^^^^^^^^^

Running type checks with mypy:

::

  $ mypy care

Test coverage
^^^^^^^^^^^^^

To run the tests, check your test coverage, and generate an HTML coverage report::

    $ coverage run -m pytest
    $ coverage html
    $ open htmlcov/index.html

Running tests with py.test
~~~~~~~~~~~~~~~~~~~~~~~~~~

::

  $ pytest

Live reloading and Sass CSS compilation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Moved to `Live reloading and SASS compilation`_.

.. _`Live reloading and SASS compilation`: http://cookiecutter-django.readthedocs.io/en/latest/live-reloading-and-sass-compilation.html




Email Server
^^^^^^^^^^^^

In development, it is often nice to be able to see emails that are being sent from your application. If you choose to use `MailHog`_ when generating the project a local SMTP server with a web interface will be available.

#. `Download the latest MailHog release`_ for your OS.

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
