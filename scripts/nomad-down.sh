#!/usr/bin/env bash
set -euo pipefail

if ! curl -s http://127.0.0.1:4646/v1/agent/self >/dev/null 2>&1; then
  echo "Nomad is not running"
  rm -f nomad.pid nomad.log
  exit 0
fi

echo "Stopping jobs..."

nomad job stop care-backend 2>/dev/null || true
nomad job stop care-redis 2>/dev/null || true
nomad job stop care-postgres 2>/dev/null || true

if [ -f nomad.pid ]; then
  kill "$(cat nomad.pid)" 2>/dev/null || true
  rm -f nomad.pid nomad.log
  echo "Nomad agent stopped"
else
  echo "No nomad.pid file found"
fi
