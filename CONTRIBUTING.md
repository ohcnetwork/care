# Contributing

The project is developed and maintained by developers in an Open Source manner.
Any support is welcome. You could help by writing documentation, pull-requests, report issues and/or translations.

### Getting Started

An issue with the [good first](https://github.com/ohcnetwork/care/issues?q=is%3Aissue+is%3Aopen+sort%3Aupdated-desc+label%3A%22good+first+issue%22) or [help wanted](https://github.com/ohcnetwork/care/issues?q=is%3Aissue+sort%3Aupdated-desc+label%3A%22help+wanted%22+is%3Aopen) label might be a good place to start with.

### Setting up the development environment

Install dependencies

```bash
pipenv sync --categories "packages dev-packages docs"
```

Install pre-commit hooks

```bash
pre-commit install
```

to run pre-commit on your branch:
```bash
pre-commit run --files $(git diff --name-only develop...HEAD)
```

#### Using Docker

Make sure you have docker and docker-compose installed. Then run:

```bash
make build
```



#### Using Virtualenv

Make sure you have Postgres and Redis installed on your system.

##### Setting up postgres for the first time

```bash
sudo -u postgres psql
CREATE ROLE my_username LOGIN PASSWORD 'my_password';
CREATE DATABASE care WITH OWNER = my_username;
```
put the following in your `.env` file
```bash
DATABASE_URL=postgres://<your_username>:<your_password>@localhost:5432/care
```

##### Setting up the environment

```bash
# create a virtualenv
python3 -m venv .venv
# activate the virtualenv
source .venv/bin/activate
# install dependencies
pipenv sync --categories "packages dev-packages docs"
# to read from .env file
export DJANGO_READ_DOT_ENV_FILE=true
# run migrations
python manage.py migrate
```

##### Troubleshooting Local Setup

If you're on Mac and you have installed Postgres.app Run:
```bash
export PATH=$PATH:/Applications/Postgres.app/Contents/Versions/14/bin
```

If you're pipenv install is failing on Pillow Consider installing these dependencies:
```bash
brew install libjpeg libtiff little-cms2 openjpeg webp freetype harfbuzz fribidi
```


### Setting up the database

- Seed the database with the following command:

```bash
python manage.py load_dummy_data
```

- Create a superuser

```bash
python manage.py createsuperuser
```

### Running the server

#### Using Docker

```bash
make up
```

if you want to attach the vscode debugger set `DJANGO_DEBUG=True` in `.env` file.

**Note**:  Whenever you update a ``python`` dependency or make a new migration to be executed on the database, you may have to rebuild the container by running

```bash
make re-build
```
#### Using Virtualenv

```bash
python manage.py runserver
```

### Running tests

Docker:

```bash
# To run all tests
make test
```
```bash
# To run a specific test file, class, or method:
make test path=<path_to_test>
```
Local:

```bash
python manage.py test
```

#

**Join us on Slack for more information**
