#!/usr/bin/env bash
set -euxo pipefail

echo "running migrations"
python manage.py migrate

echo "All migrations have been made successfully"

python manage.py runserver_plus 0.0.0.0:9000
