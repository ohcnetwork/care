"""
ASGI config for Care project with MCP server integration.

This module contains the ASGI application used by Django's development server
and any production ASGI deployments. It exposes a module-level variable
named ``application`` that includes both Django HTTP handling and MCP server
functionality via django-mcp.
"""

import os
import sys
from pathlib import Path

import django
from django.core.asgi import get_asgi_application
from django_mcp import mount_mcp_server
from starlette.middleware.cors import CORSMiddleware

# Setup Django environment first
BASE_DIR = Path(__file__).resolve(strict=True).parent.parent
sys.path.append(str(BASE_DIR / "care"))

# We defer to a DJANGO_SETTINGS_MODULE already in the environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

# Initialize Django
django.setup()

# Get the Django ASGI application
django_asgi_app = get_asgi_application()


# Mount the MCP server at /mcp path
# This enables:
# - SSE endpoint: http://localhost:9000/mcp/sse (for ADK connection)  
# - Messages endpoint: http://localhost:9000/mcp/messages
application = mount_mcp_server(
    django_http_app=django_asgi_app, 
    mcp_base_path='/mcp'
)

# Wrap the ASGI application with CORS so SSE endpoints also include CORS headers
# This is especially important because the MCP SSE endpoint may bypass Django's
# standard middleware chain where django-cors-headers is installed.
allowed_origins = os.getenv(
    "ASGI_CORS_ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:4174,http://localhost:4000",
).split(",")

application = CORSMiddleware(
    application,
    allow_origins=[origin.strip() for origin in allowed_origins if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)