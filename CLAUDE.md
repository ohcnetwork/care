# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is CARE?

CARE is a Digital Public Good building an open source EMR + Hospital Management system. This is the Django backend (Django 6.0 + Python 3.13 + PostgreSQL + Redis).

## Local Development Environment

### Running Locally (without Docker)

The local setup uses a Python 3.13 venv with PostgreSQL 16 and Redis running natively.

**Start services:**
```bash
# Ensure PostgreSQL 16 and Redis are running on your system
# Start Django backend on port 9000
DJANGO_SETTINGS_MODULE=config.settings.local DJANGO_READ_DOT_ENV_FILE=true .venv/bin/python manage.py runserver 0.0.0.0:9000
```

**Database:**
- PostgreSQL on localhost:5432, database `care`, user `postgres`, password `postgres`
- Config in `.env` (gitignored)

### Running with Docker

```bash
cp .env.example .env
make up               # Start all services (db, redis, minio, backend, celery)
make load-fixtures    # Load test data
make logs             # View logs
make down             # Stop services
```

## Build/Test Commands

### With Docker (Makefile)
- `make up` — Start all services
- `make build` — Build Docker images
- `make migrate` — Run database migrations
- `make makemigrations` — Create new migrations
- `make load-fixtures` — Load test/dummy data
- `make test path="care.users"` — Run specific tests
- `make test` — Run all tests
- `make ruff-fix-all` — Auto-fix linting issues

### Without Docker (venv)
```bash
pipenv run python manage.py migrate
pipenv run python manage.py load_fixtures
pipenv run python manage.py test care.users --keepdb --parallel
pipenv run ruff check --fix .
pipenv run ruff format .
```

## Code Style

- **Linter/Formatter**: Ruff (replaces black, isort, flake8)
- **Python version**: 3.13 (strict requirement)
- **Package management**: Pipenv (`Pipfile` + `Pipfile.lock`)

## Architecture

### Project Structure
```
care/                    # Main Django app
├── audit_log/          # Audit logging
├── contrib/            # Contributed modules
├── emr/                # Electronic Medical Records (core domain)
├── facility/           # Facility management
├── users/              # User management & auth
├── security/           # Roles & permissions
└── utils/              # Shared utilities
config/                 # Django configuration
├── settings/           # Settings modules (base, local, deployment, test)
├── api_router.py       # API URL routing
└── celery_app.py       # Celery task queue config
plug_config.py          # Plugin system configuration
```

### Plugin System
CARE supports a plugin architecture via `plug_config.py` and the `plugs` package. Plugins extend core functionality without modifying the main codebase. Be aware of plugin interfaces when modifying core models or APIs.

### Settings
- **Local dev**: `config.settings.local` (DEBUG=True, CORS open, email to console)
- **Tests**: `config.settings.test`
- **Production**: `config.settings.deployment`

### API
- Django REST Framework with `drf-nested-routers`
- JWT auth via `djangorestframework-simplejwt`
- API docs via `drf-spectacular` (OpenAPI/Swagger)
- Routes in `config/api_router.py`

### Test Credentials

Test credentials are available in the fixture data loaded by `make load-fixtures` or `python manage.py load_fixtures`.

## Git Workflow

- Default branch: `develop`
- Branch naming: `issues/{issue#}/{short-name}`

## Autonomous AI Workflow

When working autonomously:

1. **Before coding:** Read the relevant model, resource spec, authorization controller, viewset, and test files
2. **After changes:** Run `ruff check --fix .` and `ruff format .` to lint and format
3. **Verify:** Run related tests: `pipenv run python manage.py test care.module_name --keepdb`
4. **Migrations:** Run `makemigrations` after model changes, then `migrate`
