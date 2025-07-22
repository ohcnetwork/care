#!/bin/sh

mc alias set minio http://minio:9000 "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY"
mc alias set s3 https://s3.amazonaws.com "$S3_ACCESS_KEY_ID" "$S3_SECRET_ACCESS_KEY"

mc mirror minio/"$PATIENT_MINIO_BUCKET" s3/"$S3_BUCKET/$PATIENT_S3_PREFIX"
mc mirror minio/"$FACILITY_MINIO_BUCKET" s3/"$S3_BUCKET/$FACILITY_S3_PREFIX"
