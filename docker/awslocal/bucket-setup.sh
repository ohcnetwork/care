#!/usr/bin/env bash
set -x
awslocal s3 mb s3://patient-bucket
awslocal s3 mb s3://facility-bucket
set +x