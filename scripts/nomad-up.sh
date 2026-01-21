#!/usr/bin/env bash
set -euo pipefail

echo "🚀 Starting Nomad dev agent..."

if pgrep -x nomad >/dev/null 2>&1; then
  echo "✓ Nomad agent already running"
else
  nomad agent -dev > nomad.log 2>&1 &
  echo $! > nomad.pid
  echo "✓ Nomad started"
fi

echo "⏳ Waiting for Nomad..."
for i in {1..20}; do
  nomad node status >/dev/null 2>&1 && break
  sleep 1
done

if ! nomad node status >/dev/null 2>&1; then
  echo "❌ Nomad failed to start"
  exit 1
fi

echo "📦 Deploying Postgres..."
nomad job run nomad/postgres.nomad

echo "📦 Deploying Redis..."
nomad job run nomad/redis.nomad

echo "📦 Deploying Care API..."
nomad job run nomad/care-backend.nomad

echo "✅ Deployment complete"
echo "👉 Nomad UI: http://127.0.0.1:4646"
