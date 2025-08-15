{
  description = "CARE -  Care is a Digital Public Good enabling TeleICU & Decentralised Administration of Healthcare Capacity across States.";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        python = pkgs.python313;

        # Create a Python environment with pip-installable packages
        pythonEnv = python.withPackages (ps: with ps; [
          pip
          setuptools
          wheel
          virtualenv
        ]);

        # Environment variables for development
        envVars = {
          # Database
          POSTGRES_USER = "postgres";
          POSTGRES_PASSWORD = "postgres";
          POSTGRES_HOST = "localhost";
          POSTGRES_DB = "care";
          POSTGRES_PORT = "5432";
          DATABASE_URL = "postgres://postgres:postgres@localhost:5432/care";

          # Redis
          REDIS_URL = "redis://localhost:6379";
          CELERY_BROKER_URL = "redis://localhost:6379/0";

          # Django
          DJANGO_DEBUG = "true";
          ATTACH_DEBUGGER = "false";
          DJANGO_SETTINGS_MODULE = "config.settings.local";

          # MinIO/S3
          BUCKET_REGION = "ap-south-1";
          BUCKET_KEY = "minioadmin";
          BUCKET_SECRET = "minioadmin";
          BUCKET_ENDPOINT = "http://localhost:9100";
          BUCKET_EXTERNAL_ENDPOINT = "http://localhost:9100";
          FILE_UPLOAD_BUCKET = "patient-bucket";
          FACILITY_S3_BUCKET = "facility-bucket";

          # HCX Config (for local testing)
          HCX_AUTH_BASE_PATH = "https://staging-hcx.swasth.app/auth/realms/swasth-health-claim-exchange/protocol/openid-connect/token";
          HCX_ENCRYPTION_PRIVATE_KEY_URL = "https://raw.githubusercontent.com/Swasth-Digital-Health-Foundation/hcx-platform/main/demo-app/server/resources/keys/x509-private-key.pem";
          HCX_IG_URL = "https://ig.hcxprotocol.io/v0.7.1";
          HCX_PARTICIPANT_CODE = "qwertyreboot.gmail@swasth-hcx-staging";
          HCX_PASSWORD = "Opensaber@123";
          HCX_PROTOCOL_BASE_PATH = "http://staging-hcx.swasth.app/api/v0.7";
          HCX_USERNAME = "qwertyreboot@gmail.com";
          HCX_CERT_URL = "https://raw.githubusercontent.com/Swasth-Digital-Health-Foundation/hcx-platform/main/demo-app/server/resources/keys/x509-self-signed-certificate.pem";

          # Typst
          TYPST_VERSION = "0.12.0";

          # PostgreSQL configuration for compilation
          PG_CONFIG = "${pkgs.postgresql_15}/bin/pg_config";
          LDFLAGS = "-L${pkgs.postgresql_15}/lib";
          CPPFLAGS = "-I${pkgs.postgresql_15}/include";
        };

        # Helper scripts
        makeScript = name: text: pkgs.writeShellScriptBin name ''
          set -euo pipefail
          ${text}
        '';

        # Install Typst
        typstInstaller = makeScript "install-typst" ''
          if ! command -v typst >/dev/null 2>&1; then
            echo "Installing Typst v${envVars.TYPST_VERSION}..."
            TYPST_INSTALL_DIR="$HOME/.local/bin" TYPST_VERSION="${envVars.TYPST_VERSION}" ./scripts/install_typst.sh
            export PATH="$HOME/.local/bin:$PATH"
          else
            echo "Typst already installed"
          fi
        '';

        # Service management scripts
        startServices = makeScript "start-services" ''
          echo "Starting PostgreSQL..."
          if ! pgrep -x "postgres" > /dev/null; then
            mkdir -p ~/.local/share/postgres/sockets
            initdb -D ~/.local/share/postgres -U postgres --auth=trust || true

            # Configure socket directory
            echo "unix_socket_directories = '$HOME/.local/share/postgres/sockets'" >> ~/.local/share/postgres/postgresql.conf

            pg_ctl -D ~/.local/share/postgres -l ~/.local/share/postgres/logfile start
            sleep 2
            createdb -U postgres care || echo "Database 'care' already exists"
          else
            echo "PostgreSQL already running"
          fi

          echo "Starting Redis..."
          if ! pgrep -x "redis-server" > /dev/null; then
            redis-server --daemonize yes --bind 127.0.0.1 --port 6379
          else
            echo "Redis already running"
          fi

          echo "Starting MinIO..."
          if ! pgrep -x "minio" > /dev/null; then
            mkdir -p ~/.local/share/minio
            MINIO_ROOT_USER="${envVars.BUCKET_KEY}" MINIO_ROOT_PASSWORD="${envVars.BUCKET_SECRET}" \
            minio server ~/.local/share/minio --address ":9100" --console-address ":9001" &
            sleep 3
          else
            echo "MinIO already running"
          fi

          echo "All services started!"
        '';

        stopServices = makeScript "stop-services" ''
          echo "Stopping services..."
          pkill postgres || true
          pkill redis-server || true
          pkill minio || true
          echo "Services stopped"
        '';

        # Kill all development processes
        killAll = makeScript "kill-care" ''
          echo "🛑 Stopping all Care development processes..."

          # Stop Django development server
          echo "Stopping Django development server..."
          pkill -f "runserver_plus" || true
          pkill -f "manage.py runserver" || true
          pkill -f "python.*manage.py" || true

          # Stop Celery workers and beat
          echo "Stopping Celery workers..."
          pkill -f "celery.*worker" || true
          pkill -f "celery.*beat" || true
          pkill -f "watchmedo.*celery" || true

          # Stop debugpy if running
          echo "Stopping debugger..."
          pkill -f "debugpy" || true

          # Stop background services
          echo "Stopping background services..."
          pkill postgres || true
          pkill redis-server || true
          pkill minio || true

          # Clean up any remaining Python processes that might be related
          echo "Cleaning up remaining processes..."
          pkill -f "python.*config.celery_app" || true

          # Wait a moment for processes to terminate
          sleep 2

          # Force kill any stubborn processes
          echo "Force killing stubborn processes..."
          pkill -9 -f "runserver_plus" 2>/dev/null || true
          pkill -9 -f "celery.*worker" 2>/dev/null || true
          pkill -9 -f "celery.*beat" 2>/dev/null || true

          echo "✅ All development processes stopped"
          echo ""
          echo "To restart:"
          echo "  start-services  # Start background services"
          echo "  rundev          # Start unified development environment"
        '';

        # Development setup
        setupDev = makeScript "setup-dev" ''
          echo "Setting up development environment..."

          # Install Python dependencies
          if [ ! -d ".venv" ]; then
            echo "Creating virtual environment..."
            python -m venv .venv
          fi

          source .venv/bin/activate

          echo "Installing Python dependencies..."
          pip install --upgrade pip pipenv
          pipenv install --dev --system

          # Install plugins
          python install_plugins.py

          # Install Typst
          ${typstInstaller}/bin/install-typst

          echo "Development environment setup complete!"
        '';

        # Django management commands
        djangoManage = makeScript "manage" ''
          source .venv/bin/activate 2>/dev/null || true
          python manage.py "$@"
        '';

        # Database operations
        migrateDb = makeScript "migrate" ''
          source .venv/bin/activate
          python manage.py migrate
        '';

        makeMigrations = makeScript "makemigrations" ''
          source .venv/bin/activate
          python manage.py makemigrations "$@"
        '';

        loadFixtures = makeScript "load-fixtures" ''
          source .venv/bin/activate
          python manage.py load_fixtures
        '';

        # Unified development server (API + Celery)
        runDev = makeScript "rundev" ''
          source .venv/bin/activate

          echo "🚀 Starting unified Care development environment..."

          # Wait for services
          ./scripts/wait_for_db.sh
          ./scripts/wait_for_redis.sh

          # Run migrations and setup (from celery scripts)
          echo "📊 Running database migrations..."
          python manage.py migrate --noinput
          python manage.py compilemessages -v 0
          python manage.py sync_permissions_roles
          python manage.py sync_valueset

          # Collect static files (from start script)
          echo "📦 Collecting static files..."
          python manage.py collectstatic --noinput

          echo "✅ Setup complete! Starting services..."

          # Start Celery worker and beat in background
          echo "🔄 Starting Celery worker with beat scheduler..."
          watchmedo auto-restart --directory=./ --pattern=*.py --recursive -- \
            celery --workdir="$(pwd)" -A config.celery_app worker -B --loglevel=INFO &

          CELERY_PID=$!

          # Cleanup function
          cleanup() {
            echo "🛑 Shutting down services..."
            kill $CELERY_PID 2>/dev/null || true
            exit 0
          }

          trap cleanup SIGINT SIGTERM

          # Wait a moment for Celery to start
          sleep 3

          # Start Django development server
          echo "🌐 Starting Django development server on http://localhost:9000..."
          if [[ "''${ATTACH_DEBUGGER:-false}" == "true" ]]; then
            echo "🐛 Debug mode enabled - waiting for debugger on port 9876..."
            python -m debugpy --wait-for-client --listen 0.0.0.0:9876 manage.py runserver_plus 0.0.0.0:9000 --print-sql
          else
            python manage.py runserver_plus 0.0.0.0:9000 --print-sql
          fi
        '';

        # Individual development server (API only)
        runServer = makeScript "runserver" ''
          source .venv/bin/activate
          ./scripts/wait_for_db.sh
          ./scripts/wait_for_redis.sh

          echo "📊 Running migrations..."
          python manage.py migrate --noinput
          python manage.py compilemessages -v 0
          python manage.py sync_permissions_roles
          python manage.py sync_valueset

          echo "📦 Collecting static files..."
          python manage.py collectstatic --noinput

          echo "🌐 Starting Django development server..."
          if [[ "''${ATTACH_DEBUGGER:-false}" == "true" ]]; then
            echo "🐛 Debug mode enabled - waiting for debugger on port 9876..."
            python -m debugpy --wait-for-client --listen 0.0.0.0:9876 manage.py runserver_plus 0.0.0.0:9000 --print-sql
          else
            python manage.py runserver_plus 0.0.0.0:9000 --print-sql
          fi
        '';

        # Individual Celery worker
        runCelery = makeScript "celery" ''
          source .venv/bin/activate
          ./scripts/wait_for_db.sh
          ./scripts/wait_for_redis.sh

          echo "📊 Running migrations..."
          python manage.py migrate --noinput
          python manage.py compilemessages -v 0
          python manage.py sync_permissions_roles
          python manage.py sync_valueset

          echo "🔄 Starting Celery worker with beat scheduler..."
          watchmedo auto-restart --directory=./ --pattern=*.py --recursive -- \
            celery --workdir="$(pwd)" -A config.celery_app worker -B --loglevel=INFO
        '';

        # Testing
        runTests = makeScript "test" ''
          source .venv/bin/activate
          python manage.py test "''${@:-}" --settings=config.settings.test --keepdb --parallel --shuffle
        '';

        runTestsNoKeep = makeScript "test-no-keep" ''
          source .venv/bin/activate
          python manage.py test "''${@:-}" --settings=config.settings.test --parallel --shuffle
        '';

        testCoverage = makeScript "test-coverage" ''
          source .venv/bin/activate
          coverage run manage.py test --settings=config.settings.test --keepdb --parallel --shuffle
          coverage combine || true
          coverage xml
          coverage report
        '';

        # Code quality
        ruffCheck = makeScript "ruff" ''
          source .venv/bin/activate
          ruff check --fix $(git diff --name-only --staged | grep -E '\.py$|/pyproject\.toml$' || echo ".")
        '';

        ruffAll = makeScript "ruff-all" ''
          source .venv/bin/activate
          ruff check .
        '';

        ruffFix = makeScript "ruff-fix-all" ''
          source .venv/bin/activate
          ruff check --fix .
        '';

        # Database backup/restore
        dumpDb = makeScript "dump-db" ''
          pg_dump -U postgres -Fc care > care_db.dump
          echo "Database dumped to care_db.dump"
        '';

        loadDb = makeScript "load-db" ''
          if [ -f "care_db.dump" ]; then
            pg_restore -U postgres --clean --if-exists -d care care_db.dump
            echo "Database restored from care_db.dump"
          else
            echo "care_db.dump not found"
            exit 1
          fi
        '';

        resetDb = makeScript "reset-db" ''
          dropdb -U postgres care -f || true
          createdb -U postgres care
          echo "Database reset"
        '';

        # Health check
        healthCheck = makeScript "healthcheck" ''
          source .venv/bin/activate
          ./scripts/healthcheck.sh
        '';

      in
      {
        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            # Python and package management
            pythonEnv

            # Databases and services
            postgresql_15  # PostgreSQL server and client
            libpq  # PostgreSQL client library
            libpq.pg_config  # pg_config tool for psycopg compilation
            redis
            minio

            # System dependencies for building Python packages
            pkg-config
            zlib
            libjpeg
            gmp
            gettext
            curl
            wget
            git

            # Development tools
            pre-commit

            # Build tools
            gcc
            gnumake

            # Development scripts
            setupDev
            startServices
            stopServices
            killAll
            djangoManage
            migrateDb
            makeMigrations
            loadFixtures
            runDev
            runServer
            runCelery
            runTests
            runTestsNoKeep
            testCoverage
            ruffCheck
            ruffAll
            ruffFix
            dumpDb
            loadDb
            resetDb
            healthCheck
            typstInstaller
          ];

          shellHook = ''
            # Add local binaries to PATH (Nix automatically adds buildInputs to PATH)
            export PATH="$HOME/.local/bin:$PATH"

            ${builtins.concatStringsSep "\n" (pkgs.lib.mapAttrsToList (name: value: "export ${name}='${value}'") envVars)}

            # Create necessary directories
            mkdir -p ~/.local/bin ~/.local/share/postgres ~/.local/share/postgres/sockets ~/.local/share/minio

            echo "🏥 Welcome to Care development environment!"
            echo ""
            echo "Available commands:"
            echo "  setup-dev          - Set up the development environment"
            echo "  start-services     - Start PostgreSQL, Redis, and MinIO"
            echo "  stop-services      - Stop background services only"
            echo "  kill-care          - 🛑 Stop ALL development processes and services"
            echo "  rundev             - 🚀 Start both API server and Celery worker (RECOMMENDED)"
            echo "  runserver          - Start Django development server only"
            echo "  celery             - Start Celery worker with beat only"
            echo "  manage <cmd>       - Run Django management commands"
            echo "  migrate            - Run database migrations"
            echo "  makemigrations     - Create new migrations"
            echo "  load-fixtures      - Load sample data"
            echo "  test               - Run tests with coverage"
            echo "  test-no-keep       - Run tests without keeping DB"
            echo "  test-coverage      - Run tests with coverage report"
            echo "  ruff               - Check and fix staged files"
            echo "  ruff-all           - Check all files"
            echo "  ruff-fix-all       - Fix all files"
            echo "  dump-db            - Backup database"
            echo "  load-db            - Restore database"
            echo "  reset-db           - Reset database"
            echo "  healthcheck        - Check application health"
            echo ""
            echo "🚀 Quick Start (Recommended):"
            echo "  1. Run 'setup-dev' to install dependencies"
            echo "  2. Run 'start-services' to start required services"
            echo "  3. Run 'rundev' to start both API server and Celery worker"
            echo ""
            echo "📋 Manual Setup:"
            echo "  1. Run 'setup-dev' to install dependencies"
            echo "  2. Run 'start-services' to start required services"
            echo "  3. Run 'migrate' to set up the database"
            echo "  4. Run 'runserver' and 'celery' in separate terminals"
            echo ""
            echo "The Django server will be available at http://localhost:9000"
            echo "MinIO console will be available at http://localhost:9001"
            echo ""

            # Auto-activate virtual environment if it exists
            if [ -d ".venv" ]; then
              source .venv/bin/activate
              echo "✅ Virtual environment activated"
            else
              echo "⚠️  Run 'setup-dev' to create virtual environment and install dependencies"
            fi

            # Verify pg_config is available
            if command -v pg_config >/dev/null 2>&1; then
              echo "✅ PostgreSQL development tools available"
            else
              echo "❌ PostgreSQL development tools not found in PATH"
            fi
          '';
        };

        # Additional outputs for flexibility
        packages.default = pkgs.writeShellApplication {
          name = "care-dev";
          runtimeInputs = [ pythonEnv ];
          text = ''
            echo "Care development environment package"
            echo "Use 'nix develop' to enter the development shell"
          '';
        };
      });
}
