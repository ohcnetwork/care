#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

printf "api" > /tmp/container-role

if [ -z "${DATABASE_URL}" ]; then
    export DATABASE_URL="postgres://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"
fi

postgres_ready() {
python << END
import sys

import psycopg

try:
    psycopg.connect(conninfo="${DATABASE_URL}")
except psycopg.OperationalError:
    sys.exit(-1)
sys.exit(0)

END
}
until postgres_ready; do
  >&2 echo 'Waiting for PostgreSQL to become available...'
  sleep 1
done
>&2 echo 'PostgreSQL is available'

python manage.py collectstatic --noinput

export NEW_RELIC_CONFIG_FILE=/etc/newrelic.ini

python manage.py compilemessages
newrelic-admin run-program gunicorn config.wsgi:application --bind 0.0.0.0:9000 --chdir=/app
