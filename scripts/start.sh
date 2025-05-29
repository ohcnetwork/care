#!/bin/bash
printf "api" > /tmp/container-role

set -eo pipefail

if [ -z "${DATABASE_URL}" ]; then
  export DATABASE_URL="postgres://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"
fi

if [ -z "${REDIS_URL}" ]; then
  export REDIS_URL="rediss://:${REDIS_AUTH_TOKEN}@${REDIS_HOST}:${REDIS_PORT}/${REDIS_DATABASE}?ssl_cert_reqs=none"
fi


# https://docs.gunicorn.org/en/stable/settings.html#access-log-format
GUNICORN_LOG_FORMAT="${GUNICORN_LOG_FORMAT:="%(h)s %(l)s %(t)s \"%(r)s\" %(s)s %(M)s %(b)s \"%(f)s\" \"%(a)s\""}"
GUNICORN_ACCESS_LOGFILE="${GUNICORN_ACCESS_LOGFILE:="-"}"
GUNICORN_ERROR_LOGFILE="${GUNICORN_ERROR_LOGFILE:="-"}"

./wait_for_db.sh
./wait_for_redis.sh

python manage.py collectstatic --noinput
python manage.py compilemessages -v 0


gunicorn --config python:config.gunicorn config.wsgi:application --bind 0.0.0.0:9000 --chdir=/app --workers 2 \
  --access-logformat "$GUNICORN_LOG_FORMAT" --access-logfile $GUNICORN_ACCESS_LOGFILE --error-logfile $GUNICORN_ERROR_LOGFILE

