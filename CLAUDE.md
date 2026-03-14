# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is CARE?

CARE is a Digital Public Good building an open source EMR + Hospital Management system. This is the Django backend (Django 6.0 + Python 3.13 + PostgreSQL + Redis).

## Local Development Environment

### Running Locally (without Docker)

The local setup uses a Python 3.13 venv at `/home/user/care/.venv` with PostgreSQL 16 and Redis running natively.

**Start services:**
```bash
# Ensure PostgreSQL and Redis are running
pg_isready || sudo pg_ctlcluster 16 main start
redis-cli ping || redis-server --daemonize yes

# Start Django backend on port 9000
cd /home/user/care
DJANGO_SETTINGS_MODULE=config.settings.local DJANGO_READ_DOT_ENV_FILE=true .venv/bin/python manage.py runserver 0.0.0.0:9000
```

Or use: `/home/user/start-backend.sh`

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
.venv/bin/python manage.py migrate
.venv/bin/python manage.py load_fixtures
.venv/bin/python manage.py test care.users --keepdb --parallel
.venv/bin/ruff check --fix .
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
├── emr/                # Electronic Medical Records (core domain)
├── facility/           # Facility management
├── users/              # User management & auth
├── security/           # Roles & permissions
└── utils/              # Shared utilities
config/                 # Django configuration
├── settings/           # Settings modules (base, local, deployment, test)
├── api_router.py       # API URL routing
└── celery_app.py       # Celery task queue config
```

### Settings
- **Local dev**: `config.settings.local` (DEBUG=True, CORS open, email to console)
- **Tests**: `config.settings.test`
- **Production**: `config.settings.deployment`

### API
- Django REST Framework with `drf-nested-routers`
- JWT auth via `djangorestframework-simplejwt`
- API docs via `drf-spectacular` (OpenAPI/Swagger)
- Routes in `config/api_router.py`

### Test Credentials (from fixtures)

| Role | Username | Password |
|------|----------|----------|
| Doctor | `doctor_2_0` | `Coronasafe@123` |
| Admin | `administrator_2_0` | `Coronasafe@123` |
| Nurse | `nurse_2_0` | `Coronasafe@123` |
| Facility Admin | `facility_admin_2_0` | `Coronasafe@123` |

## Git Workflow

- Default branch: `develop`
- Branch naming: `issues/{issue#}/{short-name}`

## Autonomous AI Workflow

When working autonomously:

1. **Before coding:** Read the relevant model, serializer, viewset, and test files
2. **After changes:** Run `ruff check --fix .` to lint
3. **Verify:** Run related tests: `.venv/bin/python manage.py test care.module_name --keepdb`
4. **For API changes:** Update the corresponding frontend in `/home/user/care_fe`
5. **Migrations:** Run `makemigrations` after model changes, then `migrate`
