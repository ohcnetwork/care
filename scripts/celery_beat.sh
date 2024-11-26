#!/bin/bash
printf "celery-beat" > /tmp/container-role

set -euo pipefail

./wait_for_db.sh
./wait_for_redis.sh

python manage.py migrate --noinput
python manage.py compilemessages -v 0
python manage.py load_redis_index

touch /tmp/healthy

export NEW_RELIC_CONFIG_FILE=/etc/newrelic.ini
if [[ -f "$NEW_RELIC_CONFIG_FILE" ]]; then
    newrelic-admin run-program celery --app=config.celery_app beat --loglevel=info
else
    celery --app=config.celery_app beat --loglevel=info
fi
