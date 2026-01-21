#!/usr/bin/env bash
set -euo pipefail

echo "🛑 Stopping jobs..."

nomad job stop care-backend || true
nomad job stop care-redis || true
nomad job stop care-postgres || true

if [ -f nomad.pid ]; then
  kill "$(cat nomad.pid)"
  rm nomad.pid
  rm nomad.log
  echo "✓ Nomad agent stopped"
else
  echo "No nomad.pid file found"
fi
