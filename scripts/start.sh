#!/bin/bash
printf "api" > /tmp/container-role

set -euo pipefail

./wait_for_db.sh
./wait_for_redis.sh

python manage.py collectstatic --noinput
python manage.py compilemessages -v 0

export NEW_RELIC_CONFIG_FILE=/etc/newrelic.ini
if [[ -f "$NEW_RELIC_CONFIG_FILE" ]]; then
  newrelic-admin run-program gunicorn config.wsgi:application --bind 0.0.0.0:9000 --chdir=/app
else
  gunicorn config.wsgi:application --bind 0.0.0.0:9000 --chdir=/app --workers 2
fi
