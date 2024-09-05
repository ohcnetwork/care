#!/usr/bin/env bash
set -euo pipefail

printf "api" > /tmp/container-role

cd /app

echo "running collectstatic..."
python manage.py collectstatic --noinput
python manage.py compilemessages

echo "starting server..."
if [[ "${DJANGO_DEBUG,,}" == "true" ]]; then
  echo "waiting for debugger..."
  python -m debugpy --wait-for-client --listen 0.0.0.0:9876 manage.py runserver_plus 0.0.0.0:9000
else
  python manage.py runserver 0.0.0.0:9000
fi
