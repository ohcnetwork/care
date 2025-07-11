#!/bin/bash

set -e

until pg_isready -h $POSTGRES_MASTER_HOST -p $POSTGRES_MASTER_PORT -U postgres; do
  echo "Waiting for master PostgreSQL to be ready..."
  sleep 2
done

# Determine which slave this is (for replication slot)
SLAVE_NUM=${HOSTNAME##*-}
if [[ "$SLAVE_NUM" == "slave1" ]]; then
    REPLICATION_SLOT="slave1_slot"
elif [[ "$SLAVE_NUM" == "slave2" ]]; then
    REPLICATION_SLOT="slave2_slot"
else
    REPLICATION_SLOT="slave1_slot"  # fallback
fi

# Perform base backup from master to initialize the replica
export PGPASSWORD=replicator
pg_basebackup -h $POSTGRES_MASTER_HOST -p $POSTGRES_MASTER_PORT -U replicator \
  -D /var/lib/postgresql/data -v -P --slot=$REPLICATION_SLOT

# Create the standby signal file to indicate this is a standby server
touch /var/lib/postgresql/data/standby.signal

cat >> /var/lib/postgresql/data/postgresql.conf << EOF
hot_standby = on
max_standby_streaming_delay = 30s
wal_receiver_status_interval = 10s
hot_standby_feedback = on
primary_conninfo = 'host=$POSTGRES_MASTER_HOST port=$POSTGRES_MASTER_PORT user=replicator password=replicator application_name=$HOSTNAME'
primary_slot_name = '$REPLICATION_SLOT'
EOF
