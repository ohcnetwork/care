#!/bin/bash

set -e

until pg_isready -U postgres; do
  echo "Waiting for PostgreSQL to be ready..."
  sleep 2
done

psql -U postgres -c "CREATE USER replicator REPLICATION LOGIN PASSWORD 'replicator';" || {
  echo "Replication user already exists."
}

cat >> /var/lib/postgresql/data/postgresql.conf << EOF
wal_level = replica
max_wal_senders = 3
max_replication_slots = 3
hot_standby = on
wal_keep_size = 1GB
EOF

# Configure pg_hba.conf for replication connections
echo "host replication replicator all md5" >> /var/lib/postgresql/data/pg_hba.conf
pg_ctl reload -D /var/lib/postgresql/data

psql -U postgres -c "SELECT pg_create_physical_replication_slot('slave1_slot');" || {
  echo "Replication slot slave1_slot already exists."
}
psql -U postgres -c "SELECT pg_create_physical_replication_slot('slave2_slot');" || {
  echo "Replication slot slave2_slot already exists."
}
