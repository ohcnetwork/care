#!/bin/sh

# Start MinIO in the background
minio server /data --console-address ":9001" &

# Wait for MinIO to be ready before running the initialization script
TIMEOUT=300  # 5 minutes
start_time=$(date +%s)
until curl -s http://localhost:9000/minio/health/ready; do
    current_time=$(date +%s)
    elapsed=$((current_time - start_time))
    if [ $elapsed -gt $TIMEOUT ]; then
        echo "MinIO failed to start after ${TIMEOUT} seconds. But I'm sure you knew that could happen."
        exit 1
    fi
	echo "Waiting for MinIO to be ready..."
	sleep 5
done

# Run the bucket setup script
sh /init-script.sh

# Keep the container running
wait $!
