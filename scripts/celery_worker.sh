#!/bin/bash
printf "celery-worker" > /tmp/container-role

set -euo pipefail

./wait_for_db.sh
./wait_for_redis.sh

python manage.py collectstatic --noinput
python manage.py compilemessages -v 0

export NEW_RELIC_CONFIG_FILE=/etc/newrelic.ini
if [[ -f "$NEW_RELIC_CONFIG_FILE" ]]; then
    newrelic-admin run-program celery --app=config.celery_app worker --max-tasks-per-child=6 --loglevel=info
else
    celery --app=config.celery_app worker --max-tasks-per-child=6 --loglevel=info
fi
