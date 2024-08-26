#!/bin/bash
printf "celery-worker" > /tmp/container-role

if [ -z "${DATABASE_URL}" ]; then
    export DATABASE_URL="postgres://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"
fi


export NEW_RELIC_CONFIG_FILE=/etc/newrelic.ini
python manage.py collectstatic --noinput
python manage.py compilemessages
newrelic-admin run-program celery --app=config.celery_app worker --max-tasks-per-child=6 --loglevel=info
