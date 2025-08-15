#!/usr/bin/env bash
# Nix Development Environment Quick Setup Script for CARE
# This script helps new developers get started quickly with the CARE project using Nix

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🏥 Care Development Environment Setup"
echo "======================================"

# Check if Nix is installed
if ! command -v nix >/dev/null 2>&1; then
    echo "❌ Nix is not installed. Please install Nix first:"
    echo "   curl --proto '=https' --tlsv1.2 -sSf -L https://install.determinate.systems/nix | sh -s -- install"
    echo "   or visit: https://nixos.org/download.html"
    echo "determinate systems nix is preffered as it offers easier installtion 1 click uninstallation support"
    exit 1
fi

echo "✅ Nix is installed"

# Check if flakes are enabled
if ! nix flake --help >/dev/null 2>&1; then
    echo "⚠️  Nix flakes are not enabled. Adding experimental features..."
    mkdir -p ~/.config/nix
    echo "experimental-features = nix-command flakes" >> ~/.config/nix/nix.conf
fi

echo "✅ Nix flakes are available"

# Navigate to project root
cd "$PROJECT_ROOT"

echo ""
echo "🔧 Setting up development environment..."

# Enter development shell and run setup
nix develop --command bash -c "
    echo '📦 Installing Python dependencies...'
    setup-dev

    echo ''
    echo '🚀 Starting services...'
    start-services

    echo ''
    echo '🗄️  Setting up database...'
    sleep 3  # Wait for services to fully start
    migrate

    echo ''
    echo '📊 Loading sample data (optional)...'
    read -p 'Load sample fixtures? (y/N): ' -n 1 -r
    echo
    if [[ \$REPLY =~ ^[Yy]$ ]]; then
        load-fixtures || echo 'Failed to load fixtures - continuing anyway'
    fi

    echo ''
    echo '✅ Setup complete!'
    echo ''
    echo '🎉 Your Care development environment is ready!'
    echo ''
    echo '🚀 Quick Start:'
    echo '  1. Run: nix develop'
    echo '  2. Run: rundev       (starts both Django server and Celery worker)'
    echo ''
    echo '📋 Alternative (Manual):'
    echo '  1. Run: nix develop'
    echo '  2. Run: runserver    (Django server only)'
    echo '  3. In another terminal, run: nix develop --command celery'
    echo ''
    echo 'Available services:'
    echo '  - Django server: http://localhost:9000'
    echo '  - MinIO console: http://localhost:9001 (admin/minioadmin)'
    echo '  - PostgreSQL: localhost:5432 (postgres/postgres)'
    echo '  - Redis: localhost:6379'
    echo ''
    echo 'Useful commands:'
    echo '  - rundev           🚀 Start both API server and Celery worker (RECOMMENDED)'
    echo '  - runserver        Start Django development server only'
    echo '  - celery           Start Celery worker and beat only'
    echo '  - manage <cmd>     Run Django management commands'
    echo '  - test             Run tests'
    echo '  - ruff-all         Check code style'
    echo '  - kill-care        🛑 Stop ALL development processes and services'
    echo '  - stop-services    Stop background services only'
    echo ''
"

echo ""
echo "🏁 Setup script completed!"
echo ""
echo "To start developing:"
echo "  nix develop"
echo ""
echo "If you encounter any issues:"
echo "  - Check that all services are running: ps aux | grep -E 'postgres|redis|minio'"
echo "  - Restart services: stop-services && start-services"
echo ""
echo "Happy Developing! 🚀"
