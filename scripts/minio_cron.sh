#!/bin/sh

echo "Installing packages..."
apk update && apk add --no-cache dcron curl
curl -o /usr/local/bin/mc https://dl.min.io/client/mc/release/linux-amd64/mc
chmod +x /usr/local/bin/mc

cat > /backup.sh << 'EOF'
#!/bin/sh
until /usr/local/bin/mc alias set minio http://minio:9000 "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY" 2>/dev/null; do
    echo "$(date): Waiting for MinIO..."
    sleep 2
done

/usr/local/bin/mc mb --ignore-existing minio/"$PATIENT_MINIO_BUCKET"
/usr/local/bin/mc mb --ignore-existing minio/"$FACILITY_MINIO_BUCKET"

/usr/local/bin/mc alias set s3 https://s3.amazonaws.com "$S3_ACCESS_KEY_ID" "$S3_SECRET_ACCESS_KEY"

echo "$(date): Syncing patient bucket..."
/usr/local/bin/mc mirror minio/"$PATIENT_MINIO_BUCKET" s3/"$S3_BUCKET/patient-backup"

echo "$(date): Syncing facility bucket..."
/usr/local/bin/mc mirror minio/"$FACILITY_MINIO_BUCKET" s3/"$S3_BUCKET/facility-backup"

echo "$(date): Backup completed successfully!"
EOF

chmod +x /backup.sh

echo "30 18 * * * /backup.sh >> /var/log/backup.log 2>&1" | crontab -
echo "$(date): Cron job set up. Starting cron daemon..."
crond -f -l 2
