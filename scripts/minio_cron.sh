#!/bin/sh

until mc alias set minio http://minio:9000 "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY" 2>/dev/null; do
  echo "Waiting for MinIO.."
  sleep 2
done

mc mb --ignore-existing minio/"$PATIENT_MINIO_BUCKET"
mc mb --ignore-existing minio/"$FACILITY_MINIO_BUCKET"

mc alias set s3 https://s3.amazonaws.com "$S3_ACCESS_KEY_ID" "$S3_SECRET_ACCESS_KEY"

mc mirror minio/"$PATIENT_MINIO_BUCKET" s3/"$S3_BUCKET/backup"
mc mirror minio/"$FACILITY_MINIO_BUCKET" s3/"$S3_BUCKET/backup"
