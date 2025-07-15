#!/bin/bash

set -e

until pg_isready -U postgres; do
  echo "Waiting for PostgreSQL to be ready..."
  sleep 2
done

psql -U postgres -c "CREATE USER replicator REPLICATION LOGIN PASSWORD 'replicator';" || {
  echo "Replication user already exists."
}

# Only modify postgresql.conf if not already modified
CONF="/var/lib/postgresql/data/postgresql.conf"
if ! grep -q "wal_level = replica" "$CONF"; then
  cat >> "$CONF" << EOF
wal_level = replica
max_wal_senders = 3
max_replication_slots = 3
hot_standby = on
wal_keep_size = 1GB
EOF
fi

# Configure pg_hba.conf for replication connections
HBA="/var/lib/postgresql/data/pg_hba.conf"
if ! grep -q "^host replication replicator" "$HBA"; then
  echo "host replication replicator all md5" >> "$HBA"
fi

pg_ctl reload -D /var/lib/postgresql/data

psql -U postgres -c "SELECT pg_create_physical_replication_slot('slave1_slot');" || {
  echo "Replication slot slave1_slot already exists."
}
psql -U postgres -c "SELECT pg_create_physical_replication_slot('slave2_slot');" || {
  echo "Replication slot slave2_slot already exists."
}
