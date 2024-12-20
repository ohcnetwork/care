#!/bin/sh

set -e

# MinIO configuration
MINIO_HOST=${MINIO_HOST:-"http://localhost:9000"}
MINIO_ACCESS_KEY=${MINIO_ACCESS_KEY:-"minioadmin"}
MINIO_SECRET_KEY=${MINIO_SECRET_KEY:-"minioadmin"}

# Max retries and delay
MAX_RETRIES=10
RETRY_COUNT=0
RETRY_DELAY=5  # 5 seconds delay between retries

# Function to retry a command
retry_command() {
    cmd=$1
    until $cmd; do
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
            echo "Command failed after $MAX_RETRIES attempts. Exiting..."
            exit 1
        fi
        echo "Command failed. Retrying ($RETRY_COUNT/$MAX_RETRIES)..."
        sleep $RETRY_DELAY
    done
}

# Function to create a bucket if it doesn't exist
create_bucket_if_not_exists() {
    BUCKET_NAME=$1
    echo "Checking if bucket $BUCKET_NAME exists..."
    if mc ls local/$BUCKET_NAME > /dev/null 2>&1; then
        echo "Bucket $BUCKET_NAME already exists. Skipping creation."
    else
        echo "Creating bucket $BUCKET_NAME..."
        mc mb local/$BUCKET_NAME
    fi
}

# Function to set a bucket public
set_bucket_public() {
    BUCKET_NAME=$1
	# WARNING: This bucket is intentionally set to public access as MinIO doesn't support ACLs
    # Ensure only non-sensitive data is stored in this bucket
    echo "Setting bucket $BUCKET_NAME as public..."
    mc anonymous set public local/$BUCKET_NAME
}

# Retry MinIO Client alias setup
retry_command "mc alias set local $MINIO_HOST $MINIO_ACCESS_KEY $MINIO_SECRET_KEY"

# Create the necessary buckets
create_bucket_if_not_exists "patient-bucket"
create_bucket_if_not_exists "facility-bucket"

# Set only facility-bucket as public
set_bucket_public "facility-bucket"

# Graceful exit
echo "Bucket setup completed successfully."
exit 0
