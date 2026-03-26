#!/bin/bash
set -e

echo "⏳ Waiting for Docker daemon..."
while ! docker info > /dev/null 2>&1; do
  sleep 1
done
echo "✅ Docker is ready"

export DOCKER_API_VERSION=1.43
echo "🚀 Starting CARE services..."
make build-up-live
