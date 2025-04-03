#!/bin/bash
printf "celery-beat" > /tmp/container-role

set -eo pipefail

if [ -z "${DATABASE_URL}" ]; then
  export DATABASE_URL="postgres://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"
fi

if [ -z "${REDIS_URL}" ]; then
  export REDIS_URL="rediss://:${REDIS_AUTH_TOKEN}@${REDIS_HOST}:${REDIS_PORT}/${REDIS_DATABASE}?ssl_cert_reqs=none"
fi


./wait_for_db.sh
./wait_for_redis.sh

python manage.py migrate --noinput
python manage.py compilemessages -v 0
python manage.py sync_permissions_roles
python manage.py sync_valueset

touch /tmp/healthy

export NEW_RELIC_CONFIG_FILE=/etc/newrelic.ini
if [[ -f "$NEW_RELIC_CONFIG_FILE" ]]; then
    newrelic-admin run-program celery --app=config.celery_app beat --loglevel=info
else
    celery --app=config.celery_app beat --loglevel=info
fi
