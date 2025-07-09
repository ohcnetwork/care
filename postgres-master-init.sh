#!/bin/bash
set -e

# Wait for PostgreSQL to be ready
until pg_isready -U postgres; do
  echo "Waiting for PostgreSQL to be ready..."
  sleep 2
done

# Create replication user
psql -U postgres -c "CREATE USER replicator REPLICATION LOGIN PASSWORD 'replicator';"

# Configure PostgreSQL for replication
cat >> /var/lib/postgresql/data/postgresql.conf << EOF

# Replication settings
wal_level = replica
max_wal_senders = 3
max_replication_slots = 3
hot_standby = on
archive_mode = on
archive_command = 'test ! -f /var/lib/postgresql/archive/%f && cp %p /var/lib/postgresql/archive/%f'
wal_keep_segments = 64
EOF

# Configure pg_hba.conf to allow replication connections
echo "host replication replicator all md5" >> /var/lib/postgresql/data/pg_hba.conf

# Create archive directory
mkdir -p /var/lib/postgresql/archive

# Create replication slots for slaves
psql -U postgres -c "SELECT pg_create_physical_replication_slot('slave1_slot');"
psql -U postgres -c "SELECT pg_create_physical_replication_slot('slave2_slot');"

# Reload configuration
pg_ctl reload -D /var/lib/postgresql/data

echo "PostgreSQL master configured for replication"
