#!/bin/bash

postgres_ready() {
python << END
import sys
import psycopg
try:
    psycopg.connect(conninfo="${DATABASE_URL}")
except psycopg.OperationalError:
    sys.exit(-1)
sys.exit(0)
END
}

MAX_RETRIES=30
RETRY_COUNT=0
until postgres_ready; do
  if [ "$RETRY_COUNT" -ge "$MAX_RETRIES" ]; then
    >&2 echo 'Failed to connect to PostgreSQL after 30 attempts. Exiting.'
    exit 1
  fi
  >&2 echo 'Waiting for PostgreSQL to become available...'
  sleep 1
  RETRY_COUNT=$((RETRY_COUNT + 1))
done
>&2 echo 'PostgreSQL is available'
