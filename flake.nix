{
  description = "CARE - Care is a Digital Public Good enabling TeleICU & Decentralised Administration of Healthcare Capacity across States.";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    { nixpkgs, flake-utils, ... }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        python = pkgs.python313;

        # procps on Linux provides pgrep/pkill; on Darwin nixpkgs procps is a stub
        # without those binaries — use the system tools instead.
        pgrep =
          if pkgs.stdenv.isDarwin then
            "/usr/bin/pgrep"
          else
            "${pgrep}";
        pkill =
          if pkgs.stdenv.isDarwin then
            "/usr/bin/pkill"
          else
            "${pkill}";

        # Create a Python environment with pip-installable packages
        pythonEnv = python.withPackages (
          ps: with ps; [
            pip
            setuptools
            wheel
            virtualenv
          ]
        );

        # Project-local data directory (still impure but isolated)
        projectDataDir = ".nix-data";
        postgresDir = "${projectDataDir}/postgres";
        redisDir = "${projectDataDir}/redis";
        minioDir = "${projectDataDir}/minio";

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

          # PostgreSQL configuration for compilation (using Nix store paths)
          # pg_config is now a separate derivation in nixpkgs (see NixOS/nixpkgs#408785)
          PG_CONFIG = "${pkgs.postgresql_15.pg_config}/bin/pg_config";
          LDFLAGS = "-L${pkgs.libpq}/lib";
          CPPFLAGS = "-I${pkgs.libpq.dev}/include";
        };

        # Helper scripts
        makeScript =
          name: text:
          pkgs.writeShellScriptBin name ''
            set -euo pipefail
            ${text}
          '';

        # Service management scripts using Nix store binaries
        startServices = makeScript "start-services" ''
          echo "📂 Using project data directory: ${projectDataDir}"
          mkdir -p ${postgresDir} ${redisDir} ${minioDir}

          echo "🐘 Starting PostgreSQL..."
          if ! ${pgrep} -x "postgres" > /dev/null; then
            # Check if database directory is corrupted or not properly initialized
            if [ -d ${postgresDir} ] && [ ! -f ${postgresDir}/PG_VERSION ]; then
              echo "Database directory exists but appears corrupted. Cleaning up..."
              rm -rf ${postgresDir}
              mkdir -p ${postgresDir}
            fi

            # Initialize database if it doesn't exist
            if [ ! -f ${postgresDir}/PG_VERSION ]; then
              echo "Initializing new PostgreSQL database..."
              ${pkgs.postgresql_15}/bin/initdb -D ${postgresDir} -U postgres --auth=trust
              # Configure to use Unix socket in project directory
              echo "unix_socket_directories = '$(pwd)/${postgresDir}'" >> ${postgresDir}/postgresql.conf
              echo "port = 5432" >> ${postgresDir}/postgresql.conf
            fi

            ${pkgs.postgresql_15}/bin/pg_ctl -D ${postgresDir} -l ${postgresDir}/logfile start
            sleep 2
            ${pkgs.postgresql_15}/bin/createdb -h localhost -U postgres care || echo "Database 'care' already exists"
          else
            echo "PostgreSQL already running"
          fi

          echo "📮 Starting Redis..."
          if ! ${pgrep} -x "redis-server" > /dev/null; then
            # Ensure Redis directory exists
            mkdir -p ${redisDir}

            ${pkgs.redis}/bin/redis-server \
              --daemonize yes \
              --bind 127.0.0.1 \
              --port 6379 \
              --dir ${redisDir} \
              --dbfilename dump.rdb
          else
            echo "Redis already running"
          fi

          echo "🗄️ Starting MinIO..."
          if ! ${pgrep} -x "minio" > /dev/null; then
            MINIO_ROOT_USER="${envVars.BUCKET_KEY}" \
            MINIO_ROOT_PASSWORD="${envVars.BUCKET_SECRET}" \
            ${pkgs.minio}/bin/minio server ${minioDir} \
              --address ":9100" \
              --console-address ":9001" &
            sleep 3
          else
            echo "MinIO already running"
          fi

          echo "✅ All services started!"
          echo "   PostgreSQL data: ${postgresDir}"
          echo "   Redis data: ${redisDir}"
          echo "   MinIO data: ${minioDir}"
        '';

        stopServices = makeScript "stop-services" ''
          PROJECT_DATA_DIR="${projectDataDir}"
          POSTGRES_DIR="$PROJECT_DATA_DIR/postgres"

          echo "🛑 Stopping services..."

          echo "Stopping PostgreSQL..."
          if [ -f "$POSTGRES_DIR/postmaster.pid" ]; then
            ${pkgs.postgresql_15}/bin/pg_ctl -D "$POSTGRES_DIR" stop
          else
            ${pkill} postgres || true
          fi

          echo "Stopping Redis..."
          ${pkill} redis-server || true

          echo "Stopping MinIO..."
          ${pkill} minio || true

          echo "✅ Services stopped"
        '';

        # Kill all development processes
        killAll = makeScript "kill-care" ''
          echo "🛑 Stopping all Care development processes..."

          # Stop Django development server
          echo "Stopping Django development server..."
          ${pkill} -f "runserver_plus" || true
          ${pkill} -f "manage.py runserver" || true
          ${pkill} -f "python.*manage.py" || true

          # Stop Celery workers and beat
          echo "Stopping Celery workers..."
          ${pkill} -f "celery.*worker" || true
          ${pkill} -f "celery.*beat" || true
          ${pkill} -f "watchmedo.*celery" || true

          # Stop debugpy if running
          echo "Stopping debugger..."
          ${pkill} -f "debugpy" || true

          # Stop background services
          echo "Stopping background services..."
          ${stopServices}/bin/stop-services

          # Clean up any remaining Python processes that might be related
          echo "Cleaning up remaining processes..."
          ${pkill} -f "python.*config.celery_app" || true

          # Wait a moment for processes to terminate
          sleep 2

          # Force kill any stubborn processes
          echo "Force killing stubborn processes..."
          ${pkill} -9 -f "runserver_plus" 2>/dev/null || true
          ${pkill} -9 -f "celery.*worker" 2>/dev/null || true
          ${pkill} -9 -f "celery.*beat" 2>/dev/null || true

          echo "✅ All development processes stopped"
          echo ""
          echo "To restart:"
          echo "  start-services  # Start background services"
          echo "  rundev          # Start unified development environment"
        '';

        # Clean project data (useful for fresh start)
        cleanData = makeScript "clean-data" ''
          PROJECT_DATA_DIR="${projectDataDir}"

          echo "⚠️  This will delete all local service data (PostgreSQL, Redis, MinIO)"
          read -p "Are you sure? (y/N) " -n 1 -r
          echo
          if [[ $REPLY =~ ^[Yy]$ ]]; then
            ${stopServices}/bin/stop-services
            echo "🗑️  Removing $PROJECT_DATA_DIR..."
            rm -rf "$PROJECT_DATA_DIR"
            echo "✅ Project data cleaned"
          else
            echo "Cancelled"
          fi
        '';

        # Development setup
        setupDev = makeScript "setup-dev" ''
          echo "🏗️  Setting up development environment..."

          # Ensure pg_config is on PATH for building psycopg-c
          # pg_config is now a separate derivation in nixpkgs (see NixOS/nixpkgs#408785)
          export PATH="${pkgs.postgresql_15.pg_config}/bin:$PATH"
          export PG_CONFIG="${pkgs.postgresql_15.pg_config}/bin/pg_config"

          # Install Python dependencies
          if [ ! -d ".venv" ]; then
            echo "Creating virtual environment..."
            ${python}/bin/python -m venv .venv
          fi

          source .venv/bin/activate

          echo "Installing Python dependencies..."
          pip install --upgrade pip pipenv
          pipenv install --dev --system

          # Install plugins
          python install_plugins.py

          echo "✅ Development environment setup complete!"
          echo ""
          echo "Note: ruff ${pkgs.ruff.version} is available from Nix store"
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

          # Wait for services (using Nix bash)
          ${pkgs.bash}/bin/bash ./scripts/wait_for_db.sh
          ${pkgs.bash}/bin/bash ./scripts/wait_for_redis.sh

          # Run migrations and setup
          echo "📊 Running database migrations..."
          python manage.py migrate --noinput
          python manage.py compilemessages -v 0
          python manage.py sync_permissions_roles
          python manage.py sync_valueset

          # Collect static files
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
          ${pkgs.bash}/bin/bash ./scripts/wait_for_db.sh
          ${pkgs.bash}/bin/bash ./scripts/wait_for_redis.sh

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
          ${pkgs.bash}/bin/bash ./scripts/wait_for_db.sh
          ${pkgs.bash}/bin/bash ./scripts/wait_for_redis.sh

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

        # Code quality (using Nix-provided ruff for NixOS compatibility)
        ruffCheck = makeScript "ruff" ''
          ${pkgs.ruff}/bin/ruff check --fix $(git diff --name-only --staged | grep -E '\.py$|/pyproject\.toml$' || echo ".")
        '';

        ruffAll = makeScript "ruff-all" ''
          ${pkgs.ruff}/bin/ruff check .
        '';

        ruffFix = makeScript "ruff-fix-all" ''
          ${pkgs.ruff}/bin/ruff check --fix .
        '';

        # Database backup/restore using Nix store binaries
        dumpDb = makeScript "dump-db" ''
          ${pkgs.postgresql_15}/bin/pg_dump -h localhost -U postgres -Fc care > care_db.dump
          echo "✅ Database dumped to care_db.dump"
        '';

        loadDb = makeScript "load-db" ''
          if [ -f "care_db.dump" ]; then
            ${pkgs.postgresql_15}/bin/pg_restore -h localhost -U postgres --clean --if-exists -d care care_db.dump
            echo "✅ Database restored from care_db.dump"
          else
            echo "❌ care_db.dump not found"
            exit 1
          fi
        '';

        resetDb = makeScript "reset-db" ''
          ${pkgs.postgresql_15}/bin/dropdb -h localhost -U postgres care -f || true
          ${pkgs.postgresql_15}/bin/createdb -h localhost -U postgres care
          echo "✅ Database reset"
        '';

        # Health check
        healthCheck = makeScript "healthcheck" ''
          source .venv/bin/activate
          ${pkgs.bash}/bin/bash ./scripts/healthcheck.sh
        '';

      in
      {
        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            # Python and package management
            pythonEnv

            # Databases and services (from Nix store)
            postgresql_15
            postgresql_15.pg_config
            libpq
            redis
            minio
            ruff # Ruff from Nix for NixOS compatibility

            # System dependencies for building Python packages
            pkg-config
            zlib
            libjpeg
            gmp
            gettext
            curl
            wget
            git

            # WeasyPrint native dependencies (loaded via cffi dlopen at runtime)
            glib
            pango
            harfbuzz
            fontconfig
            freetype
            cairo

            # Development tools
            pre-commit

            # Build tools
            gcc
            gnumake
          ]
          ++ pkgs.lib.optionals pkgs.stdenv.isLinux [
            pkgs.procps # pgrep/pkill (Darwin uses /usr/bin via processUtils above)
          ]
          ++ [
            # Development scripts
            setupDev
            startServices
            stopServices
            killAll
            cleanData
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
          ];

          shellHook = ''
            ${builtins.concatStringsSep "\n" (
              pkgs.lib.mapAttrsToList (name: value: "export ${name}='${value}'") envVars
            )}

            # WeasyPrint needs to dlopen native libs (glib, pango, etc.) at runtime
            export DYLD_FALLBACK_LIBRARY_PATH="${pkgs.lib.makeLibraryPath [
              pkgs.glib
              pkgs.pango
              pkgs.harfbuzz
              pkgs.fontconfig
              pkgs.freetype
              pkgs.cairo
            ]}''${DYLD_FALLBACK_LIBRARY_PATH:+:$DYLD_FALLBACK_LIBRARY_PATH}"

            # Create project data directory
            mkdir -p ${projectDataDir}

            # Add .nix-data to .gitignore if not already there
            if [ -f .gitignore ] && ! grep -q "^\.nix-data$" .gitignore; then
              echo ".nix-data" >> .gitignore
            fi

            echo "🏥 Welcome to Care development environment!"
            echo ""
            echo "📦 Using reproducible Nix store binaries:"
            echo "   PostgreSQL: ${pkgs.postgresql_15.version}"
            echo "   Redis: ${pkgs.redis.version}"
            echo "   MinIO: ${pkgs.minio.version}"
            echo "   Ruff: ${pkgs.ruff.version}"
            echo ""
            echo "Available commands:"
            echo "  setup-dev          - Set up the development environment"
            echo "  start-services     - Start PostgreSQL, Redis, and MinIO"
            echo "  stop-services      - Stop background services only"
            echo "  kill-care          - 🛑 Stop ALL development processes and services"
            echo "  clean-data         - 🗑️  Remove all local service data"
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
            echo "  1. Run 'setup-dev' to install Python dependencies"
            echo "  2. Run 'start-services' to start required services"
            echo "  3. Run 'rundev' to start both API server and Celery worker"
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

            # Verify tools are available
            echo "✅ PostgreSQL development tools available (${pkgs.postgresql_15.version})"
            echo "✅ Ruff available (${pkgs.ruff.version})"
          '';
        };

        # Package for CI/CD or other use cases
        packages.default = pkgs.writeShellApplication {
          name = "care-dev";
          runtimeInputs = [
            pythonEnv
            pkgs.postgresql_15
            pkgs.redis
            pkgs.minio
            pkgs.ruff
          ];
          text = ''
            echo "Care development environment package"
            echo "Use 'nix develop' to enter the development shell"
          '';
        };

        # Production OCI image built with dockerTools.
        #
        # In CI the image is built via nix-build with --argstr overrides so
        # that the pre-built .venv and checked-out source are injected.
        #
        # Locally you can test with:
        #   nix build .#dockerImage
        # (requires a .venv to exist at the repo root)
        packages.dockerImage = import ./nix/docker-image.nix {
          inherit pkgs;
          appVersion = "dev";
          venvPath = ./.venv;
          appSrc = ./.;
        };
      }
    );
}
