#!/usr/bin/env bash
printf "api" > /tmp/container-role

set -euo pipefail

./scripts/wait_for_db.sh
./scripts/wait_for_redis.sh

echo "installing plugins..."
python install_plugins.py

echo "running collectstatic..."
python manage.py collectstatic --noinput
python manage.py compilemessages -v 0

# Start ADK web server for Care Copilot (connects to django-mcp)
if [[ "${ENABLE_COPILOT_ADK}" == "true" ]]; then
  echo "starting Care Copilot ADK web server on port 8000..."
  echo "🔗 ADK agent will connect to MCP server at: http://localhost:9000/mcp/sse"
  cd /app/care_copilot && adk web . --host 0.0.0.0 --port 8000 &
  cd /app
fi

echo "starting Django server with ASGI (includes MCP server)..."
echo "🏥 MCP server will be available at: http://localhost:9000/mcp/sse"
echo "🌐 ADK web interface will be available at: http://localhost:8000"

if [[ "${ATTACH_DEBUGGER}" == "true" ]]; then
  echo "debugger enabled - attach to port 9876..."
  python -Xfrozen_modules=off -m debugpy --listen 0.0.0.0:9876 -m uvicorn config.asgi:application --host 0.0.0.0 --port 9000 --reload
else
  python -Xfrozen_modules=off -m uvicorn config.asgi:application --host 0.0.0.0 --port 9000 --reload
fi
