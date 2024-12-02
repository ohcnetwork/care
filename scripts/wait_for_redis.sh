#!/bin/bash

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
    >&2 echo 'Failed to connect to Redis after 30 attempts. Exiting.'
    exit 1
  fi
  >&2 echo 'Waiting for Redis to become available...'
  sleep 1
  RETRY_COUNT=$((RETRY_COUNT + 1))
done
>&2 echo 'Redis is available'
