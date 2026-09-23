#!/bin/bash

set -eo pipefail

export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings.deployment}"
export DATABASE_URL="${DATABASE_URL:-postgres://postgres:postgres@localhost:5432/care}"
export REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"

python manage.py compilemessages -v 0
python manage.py collectstatic --noinput "$@"
