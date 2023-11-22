#!/usr/bin/env bash
set -euo pipefail

cd /app

echo "running migrations..."
python manage.py migrate

echo "running collectstatic..."
python manage.py collectstatic --noinput

echo "starting server..."
if [[ "${DJANGO_DEBUG,,}" == "true" ]]; then
  python -m debugpy --wait-for-client --listen 0.0.0.0:9876 manage.py runserver_plus 0.0.0.0:9000
else
  python manage.py runserver 0.0.0.0:9000
fi
