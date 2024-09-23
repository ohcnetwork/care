#!/bin/bash
printf "celery-beat" > /tmp/container-role

if [ -z "${DATABASE_URL}" ]; then
    export DATABASE_URL="postgres://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"
fi

postgres_ready() {
python << END
import sys

import psycopg

try:
    psycopg.connect(conninfo="${DATABASE_URL}")
except psycopg.OperationalError as e:
    print(e)
    sys.exit(-1)
sys.exit(0)

END
}

until postgres_ready; do
  >&2 echo 'Waiting for PostgreSQL to become available...'
  sleep 1
done
>&2 echo 'PostgreSQL is available'

python manage.py migrate --noinput
python manage.py compilemessages
python manage.py load_redis_index
python manage.py load_event_types

touch /tmp/healthy

export NEW_RELIC_CONFIG_FILE=/etc/newrelic.ini
newrelic-admin run-program celery --app=config.celery_app beat --loglevel=info
