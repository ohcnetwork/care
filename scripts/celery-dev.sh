#!/bin/bash
printf "celery" > /tmp/container-role

set -euo pipefail

./scripts/wait_for_db.sh
./scripts/wait_for_redis.sh

python manage.py migrate --noinput
python manage.py compilemessages -v 0
python manage.py sync_permissions_roles
python manage.py sync_valueset

watchmedo \
    auto-restart --directory=./ --pattern=*.py --recursive -- \
    celery --workdir="$(pwd)" -A config.celery_app worker -B --loglevel=INFO
