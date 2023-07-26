#!/bin/bash

if [ -z "${DATABASE_URL}" ]; then
    export DATABASE_URL="postgres://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"
fi
export NEW_RELIC_CONFIG_FILE=/etc/newrelic.ini
newrelic-admin run-program celery --app=config.celery_app beat --loglevel=info
