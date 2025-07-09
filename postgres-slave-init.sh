#!/bin/bash
set -e

# Wait for master to be ready
until pg_isready -h $POSTGRES_MASTER_HOST -p $POSTGRES_MASTER_PORT -U postgres; do
  echo "Waiting for master PostgreSQL to be ready..."
  sleep 5
done

# Remove existing data directory if it exists
rm -rf /var/lib/postgresql/data/*

# Determine which slave this is (for replication slot)
SLAVE_NUM=${HOSTNAME##*-}
if [[ "$SLAVE_NUM" == "slave1" ]]; then
    REPLICATION_SLOT="slave1_slot"
elif [[ "$SLAVE_NUM" == "slave2" ]]; then
    REPLICATION_SLOT="slave2_slot"
else
    REPLICATION_SLOT="slave1_slot"  # fallback
fi

# Perform base backup from master
pg_basebackup -h $POSTGRES_MASTER_HOST -p $POSTGRES_MASTER_PORT -U replicator -D /var/lib/postgresql/data -v -P -W --slot=$REPLICATION_SLOT

# Create standby.signal file (modern approach)
touch /var/lib/postgresql/data/standby.signal

# Configure PostgreSQL for read-only slave
cat >> /var/lib/postgresql/data/postgresql.conf << EOF

# Slave settings
hot_standby = on
max_standby_archive_delay = 30s
max_standby_streaming_delay = 30s
wal_receiver_status_interval = 10s
hot_standby_feedback = on
primary_conninfo = 'host=$POSTGRES_MASTER_HOST port=$POSTGRES_MASTER_PORT user=replicator password=replicator application_name=$HOSTNAME'
primary_slot_name = '$REPLICATION_SLOT'
EOF

# Create trigger file directory
mkdir -p /tmp

echo "PostgreSQL slave configured and ready for replication"
