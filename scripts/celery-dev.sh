#!/bin/bash
printf "celery" > /tmp/container-role

set -euo pipefail

./scripts/wait_for_db.sh
./scripts/wait_for_redis.sh

python manage.py migrate --noinput
python manage.py compilemessages -v 0
python manage.py load_redis_index


watchmedo \
    auto-restart --directory=./ --pattern=*.py --recursive -- \
    celery --workdir="/app" -A config.celery_app worker -B --loglevel=INFO
