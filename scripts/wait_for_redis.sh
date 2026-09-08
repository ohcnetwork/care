#!/bin/bash

log_info() {
  printf '%s [INFO] [%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "${0##*/}" "$*"
}

log_error() {
  printf '%s [ERROR] [%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "${0##*/}" "$*" >&2
}

redis_ready() {
python << END
import sys
import redis
try:
    redis_client = redis.Redis.from_url("${REDIS_URL}")
    redis_client.ping()
except (redis.exceptions.ConnectionError, redis.exceptions.ResponseError):
    sys.exit(-1)
sys.exit(0)
END
}

MAX_RETRIES=30
RETRY_COUNT=0
until redis_ready; do
  if [ "$RETRY_COUNT" -ge "$MAX_RETRIES" ]; then
    log_error 'Failed to connect to Redis after 30 attempts. Exiting.'
    exit 1
  fi
  log_info 'Waiting for Redis to become available...'
  sleep 1
  RETRY_COUNT=$((RETRY_COUNT + 1))
done
log_info 'Redis is available'
