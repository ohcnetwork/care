#!/bin/sh

minio_backup() {
    until mc alias set minio http://minio:9000 "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY" 2>/dev/null; do
        echo "Waiting for MinIO..."
        sleep 2
    done

    mc mb --ignore-existing minio/"$PATIENT_MINIO_BUCKET"
    mc mb --ignore-existing minio/"$FACILITY_MINIO_BUCKET"

    mc alias set s3 https://s3.amazonaws.com "$S3_ACCESS_KEY_ID" "$S3_SECRET_ACCESS_KEY"

    echo "Syncing patient bucket..."
    mc mirror minio/"$PATIENT_MINIO_BUCKET" s3/"$S3_BUCKET/backup"

    echo "Syncing facility bucket..."
    mc mirror minio/"$FACILITY_MINIO_BUCKET" s3/"$S3_BUCKET/backup"

    echo "Backup completed successfully!"
}

if ! command -v crond >/dev/null 2>&1; then
    echo "Installing cron..."
    apt-get install -y cron
fi

echo "0 0 * * * /bin/sh -c '. /etc/environment && $(declare -f minio_backup); minio_backup' >> /var/log/backup.log 2>&1" | crontab -
crond -f -d 8
