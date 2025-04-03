#!/bin/bash

postgres_ready() {
python << END
import sys
import psycopg
try:
    con = psycopg.connect(
        user="${POSTGRES_USER}",
        password="${POSTGRES_PASSWORD}",
        host="${POSTGRES_HOST}",
        port="${POSTGRES_PORT}",
    )
    database="${POSTGRES_DB}"
    con.autocommit = True
    cursor          = con.cursor();
    cursor.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{database}'")
    exists = cursor.fetchone()
    if not exists:
        print("Creating Database")
        cursor.execute(f'CREATE DATABASE {database}')
    # rest of the script
except psycopg.OperationalError as e:
    print(e)
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
